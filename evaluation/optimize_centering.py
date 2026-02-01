"""
Merkezleme kuramı optimizasyon stratejileri ve araçları
"""
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Dict
import importlib.util
import sysconfig
from itertools import product

import requests
import torch
import stanza
import spacy_udpipe


# Work around PyTorch 2.6+ defaulting to weights_only=True
_orig_load = torch.load

def _load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_load(*args, **kwargs)


torch.load = _load


UD_URL = "https://github.com/UniversalDependencies/UD_Turkish-IMST/archive/refs/heads/master.zip"
DATA_DIR = Path("../data/ud_tr_imst")
DEV_FILE = DATA_DIR / "UD_Turkish-IMST-master" / "tr_imst-ud-dev.conllu"
TEST_FILE = DATA_DIR / "UD_Turkish-IMST-master" / "tr_imst-ud-test.conllu"


@dataclass
class Token:
    form: str
    upos: str
    head: int
    deprel: str


@dataclass
class CenteringState:
    forward_centers: List[str]
    backward_center: Optional[str]
    preferred_center: Optional[str]


def _load_transition_type():
    purelib = sysconfig.get_paths().get("purelib")
    if not purelib:
        return None
    module_path = Path(purelib) / "lgram" / "models" / "centering_theory.py"
    if not module_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("centering_theory", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "TransitionType", None)


TransitionType = _load_transition_type()


if TransitionType is None:
    class TransitionType(Enum):
        CONTINUE = "Continue"
        RETAIN = "Retain"
        SMOOTH_SHIFT = "Smooth-Shift"
        ROUGH_SHIFT = "Rough-Shift"


def download_ud_treebank():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DATA_DIR / "ud_tr_imst.zip"
    if not zip_path.exists():
        resp = requests.get(UD_URL, timeout=60)
        resp.raise_for_status()
        zip_path.write_bytes(resp.content)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(DATA_DIR)


def iter_conllu_sentences(path: Path):
    with path.open("r", encoding="utf-8") as f:
        sent_lines = []
        for line in f:
            line = line.rstrip("\n")
            if not line:
                if sent_lines:
                    yield sent_lines
                    sent_lines = []
                continue
            if line.startswith("#"):
                continue
            sent_lines.append(line)
        if sent_lines:
            yield sent_lines


def parse_sentence(lines) -> List[Token]:
    tokens = []
    for line in lines:
        cols = line.split("\t")
        if len(cols) < 8:
            continue
        tok_id = cols[0]
        if "-" in tok_id or "." in tok_id:
            continue
        tokens.append(Token(form=cols[1], upos=cols[3], head=int(cols[6]), deprel=cols[7]))
    return tokens


def stanza_parse(nlp, text: str) -> Optional[List[Token]]:
    doc = nlp(text)
    if not doc.sentences:
        return None
    words = doc.sentences[0].words
    return [Token(w.text, w.upos, w.head, w.deprel) for w in words]


def udpipe_parse(nlp, text: str) -> Optional[List[Token]]:
    doc = nlp(text)
    if not doc.sents:
        return None
    sent = list(doc.sents)[0]
    tokens = []
    for tok in sent:
        head = 0
        if tok.head != tok:
            head = tok.head.i - sent.start + 1
        tokens.append(Token(form=tok.text, upos=tok.pos_, head=head, deprel=tok.dep_))
    return tokens


def compute_forward_centers(tokens: List[Token], salience_weights: Dict, pos_weights: Dict) -> List[str]:
    """Parametrize edilmiş forward center hesaplama"""
    centers = []
    for i, tok in enumerate(tokens):
        if tok.upos not in {"NOUN", "PROPN", "PRON"}:
            continue
        salience = 0.0
        if tok.deprel in salience_weights:
            salience += salience_weights[tok.deprel]
        if tok.upos in pos_weights:
            salience += pos_weights[tok.upos]
        position_weight = 1.0 - (i / max(1, len(tokens)))
        salience += position_weight
        centers.append((tok.form.lower(), salience, i))

    centers.sort(key=lambda x: (-x[1], x[2]))

    seen = set()
    ordered = []
    for center, _, _ in centers:
        if center not in seen:
            seen.add(center)
            ordered.append(center)
    return ordered[:5]


def compute_transition(prev_state: Optional[CenteringState], current_cf: List[str]) -> Tuple[Optional[TransitionType], CenteringState]:
    cp = current_cf[0] if current_cf else None

    if prev_state is None:
        state = CenteringState(forward_centers=current_cf, backward_center=None, preferred_center=cp)
        return None, state

    prev_cb = prev_state.backward_center
    cb = None
    for prev_center in prev_state.forward_centers:
        if prev_center in current_cf:
            cb = prev_center
            break

    if cb is None:
        transition = TransitionType.ROUGH_SHIFT
    else:
        if prev_cb == cb and cb == cp:
            transition = TransitionType.CONTINUE
        elif prev_cb == cb and cb != cp:
            transition = TransitionType.RETAIN
        elif prev_cb != cb and cb == cp:
            transition = TransitionType.SMOOTH_SHIFT
        else:
            transition = TransitionType.ROUGH_SHIFT

    state = CenteringState(forward_centers=current_cf, backward_center=cb, preferred_center=cp)
    return transition, state


def transition_score(transition: Optional[TransitionType], weights: Dict) -> int:
    """Parametrize edilmiş geçiş skorlama"""
    if transition is None:
        return weights.get("INITIAL", 1)
    return weights.get(transition, 0)


def evaluate_with_weights(
    data_file: Path,
    stanza_nlp,
    udpipe_nlp,
    transition_weights: Dict,
    salience_weights: Dict,
    pos_weights: Dict
) -> Tuple[int, int]:
    """Belirli ağırlıklarla değerlendirme yap"""
    uas = 0
    total = 0
    prev_state: Optional[CenteringState] = None

    for sent_lines in iter_conllu_sentences(data_file):
        gold = parse_sentence(sent_lines)
        if not gold:
            continue

        text = " ".join(tok.form for tok in gold)
        pred_stanza = stanza_parse(stanza_nlp, text)
        pred_udpipe = udpipe_parse(udpipe_nlp, text)

        if not pred_stanza or not pred_udpipe:
            continue
        if len(pred_stanza) != len(gold) or len(pred_udpipe) != len(gold):
            continue

        # Centering skorlarını hesapla
        cf_s = compute_forward_centers(pred_stanza, salience_weights, pos_weights)
        transition_s, state_s = compute_transition(prev_state, cf_s)
        score_s = transition_score(transition_s, transition_weights)

        cf_u = compute_forward_centers(pred_udpipe, salience_weights, pos_weights)
        transition_u, state_u = compute_transition(prev_state, cf_u)
        score_u = transition_score(transition_u, transition_weights)

        # Seç
        if score_u > score_s:
            chosen = pred_udpipe
            prev_state = state_u
        else:
            chosen = pred_stanza
            prev_state = state_s

        # UAS hesapla
        for g, c in zip(gold, chosen):
            total += 1
            if c.head == g.head:
                uas += 1

    return uas, total


def optimize_weights():
    """Grid search ile en iyi ağırlıkları bul"""
    download_ud_treebank()

    if not DEV_FILE.exists():
        raise FileNotFoundError(f"Dev file not found: {DEV_FILE}")

    print("Loading parsers...")
    stanza.download("tr", verbose=False)
    stanza_nlp = stanza.Pipeline("tr", processors="tokenize,pos,lemma,depparse", tokenize_no_ssplit=False, verbose=False)
    spacy_udpipe.download("tr")
    udpipe_nlp = spacy_udpipe.load("tr")

    # Varsayılan ağırlıklar
    default_salience = {
        "nsubj": 4, "nsubjpass": 4, "obj": 3, "dobj": 3,
        "iobj": 2, "pobj": 2, "attr": 2, "oprd": 2,
        "poss": 1, "appos": 1,
    }
    default_pos = {"PRON": 3, "PROPN": 2, "NOUN": 1}

    # Geçiş ağırlıkları grid search
    print("\nOptimizing transition weights on dev set...")
    best_uas = 0
    best_weights = None

    for con in [2, 3, 4]:
        for ret in [1, 2, 3]:
            for ssh in [1, 2, 3]:
                for rsh in [0, 1, 2]:
                    weights = {
                        TransitionType.CONTINUE: con,
                        TransitionType.RETAIN: ret,
                        TransitionType.SMOOTH_SHIFT: ssh,
                        TransitionType.ROUGH_SHIFT: rsh,
                        "INITIAL": 1,
                    }
                    uas, total = evaluate_with_weights(
                        DEV_FILE, stanza_nlp, udpipe_nlp, weights, default_salience, default_pos
                    )
                    uas_score = uas / total * 100 if total > 0 else 0

                    if uas_score > best_uas:
                        best_uas = uas_score
                        best_weights = weights
                        print(f"  New best: UAS={uas_score:.2f}% | CON={con} RET={ret} SSH={ssh} RSH={rsh}")

    print(f"\nBest weights found:")
    print(f"  CONTINUE: {best_weights[TransitionType.CONTINUE]}")
    print(f"  RETAIN: {best_weights[TransitionType.RETAIN]}")
    print(f"  SMOOTH_SHIFT: {best_weights[TransitionType.SMOOTH_SHIFT]}")
    print(f"  ROUGH_SHIFT: {best_weights[TransitionType.ROUGH_SHIFT]}")
    print(f"  Dev UAS: {best_uas:.2f}%")

    # Test üzerinde değerlendir
    print("\nEvaluating on test set with optimized weights...")
    uas, total = evaluate_with_weights(
        TEST_FILE, stanza_nlp, udpipe_nlp, best_weights, default_salience, default_pos
    )
    test_uas = uas / total * 100 if total > 0 else 0
    print(f"  Test UAS: {test_uas:.2f}%")


if __name__ == "__main__":
    optimize_weights()
