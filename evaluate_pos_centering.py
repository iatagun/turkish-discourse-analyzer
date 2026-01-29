import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple
import importlib.util
import sysconfig

import requests
import torch
import stanza
import spacy_udpipe


# Work around PyTorch 2.6+ defaulting to weights_only=True in torch.load
_orig_load = torch.load

def _load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_load(*args, **kwargs)


torch.load = _load


UD_URL = "https://github.com/UniversalDependencies/UD_Turkish-IMST/archive/refs/heads/master.zip"
DATA_DIR = Path("data/ud_tr_imst")
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


TransitionType = _load_transition_type()  # type: ignore


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
        tokens.append(
            Token(
                form=cols[1],
                upos=cols[3],
                head=int(cols[6]),
                deprel=cols[7],
            )
        )
    return tokens


def stanza_parse(nlp, text: str) -> Optional[List[Token]]:
    doc = nlp(text)
    if not doc.sentences:
        return None
    words = doc.sentences[0].words
    tokens = [Token(w.text, w.upos, w.head, w.deprel) for w in words]
    return tokens


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


def compute_forward_centers(tokens: List[Token]) -> List[str]:
    """Söylemsel merkezleri POS bilgisiyle çıkar"""
    salience_weights = {
        "nsubj": 4,
        "nsubjpass": 4,
        "obj": 3,
        "dobj": 3,
        "iobj": 2,
        "pobj": 2,
        "attr": 2,
        "oprd": 2,
        "poss": 1,
        "appos": 1,
    }
    pos_weights = {
        "PRON": 3,
        "PROPN": 2,
        "NOUN": 1,
    }

    centers = []
    for i, tok in enumerate(tokens):
        # POS etiketi üzerinden merkez adaylığını kontrol et
        if tok.upos not in {"NOUN", "PROPN", "PRON"}:
            continue
        salience = 0.0
        if tok.deprel in salience_weights:
            salience += salience_weights[tok.deprel]
        # POS'a göre ağırlık - burada POS'un doğru olması önemli
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


def transition_score(transition: Optional[TransitionType]) -> int:
    if transition is None:
        return 1
    weights = {
        TransitionType.CONTINUE: 3,
        TransitionType.RETAIN: 2,
        TransitionType.SMOOTH_SHIFT: 2,
        TransitionType.ROUGH_SHIFT: 1,
    }
    return weights.get(transition, 0)


def score_parse(tokens: List[Token], prev_state: Optional[CenteringState]) -> Tuple[int, CenteringState]:
    """POS etiketleriyle oluşturulan merkezleme skorunu hesapla"""
    cf = compute_forward_centers(tokens)
    transition, state = compute_transition(prev_state, cf)
    return transition_score(transition), state


def pos_accuracy(gold: List[Token], pred: List[Token]) -> Tuple[int, int]:
    """POS doğruluk hesapla"""
    total = 0
    correct = 0
    for g, p in zip(gold, pred):
        total += 1
        if p.upos == g.upos:
            correct += 1
    return correct, total


def main():
    download_ud_treebank()

    if not TEST_FILE.exists():
        raise FileNotFoundError(f"Test file not found: {TEST_FILE}")

    stanza.download("tr", verbose=False)
    stanza_nlp = stanza.Pipeline("tr", processors="tokenize,pos,lemma,depparse", tokenize_no_ssplit=False, verbose=False)
    spacy_udpipe.download("tr")
    udpipe_nlp = spacy_udpipe.load("tr")

    counts_stanza = {"correct": 0, "total": 0}
    counts_udpipe = {"correct": 0, "total": 0}
    counts_rerank = {"correct": 0, "total": 0}

    prev_state: Optional[CenteringState] = None

    for sent_lines in iter_conllu_sentences(TEST_FILE):
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

        # Her iki parser'ın POS doğruluğunu hesapla
        c_s, t_s = pos_accuracy(gold, pred_stanza)
        counts_stanza["correct"] += c_s
        counts_stanza["total"] += t_s

        c_u, t_u = pos_accuracy(gold, pred_udpipe)
        counts_udpipe["correct"] += c_u
        counts_udpipe["total"] += t_u

        # Centering skorlarıyla sınayarak en iyi POS seçimini yap
        score_s, state_s = score_parse(pred_stanza, prev_state)
        score_u, state_u = score_parse(pred_udpipe, prev_state)

        # Daha yüksek centering skoru olan parse'ın POS etiketlerini seç
        if score_u > score_s:
            chosen = pred_udpipe
            prev_state = state_u
        else:
            chosen = pred_stanza
            prev_state = state_s

        c_r, t_r = pos_accuracy(gold, chosen)
        counts_rerank["correct"] += c_r
        counts_rerank["total"] += t_r

    def report(name: str, counts: dict) -> None:
        total = counts["total"]
        if total == 0:
            print(f"{name}: no tokens evaluated")
            return
        acc = counts["correct"] / total * 100
        print(f"{name}")
        print(f"  Tokens evaluated: {total}")
        print(f"  POS Accuracy: {acc:.2f}%")

    print("UD Turkish IMST (test) - POS Tagging with Centering-based Reranking")
    print()
    report("Stanza", counts_stanza)
    report("UDPipe", counts_udpipe)
    report("Centering rerank (POS belirsizlik azaltma)", counts_rerank)


if __name__ == "__main__":
    main()
