import io
import os
import zipfile
from pathlib import Path

import requests
import torch
import stanza


# Work around PyTorch 2.6+ defaulting to weights_only=True in torch.load
_orig_load = torch.load

def _load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_load(*args, **kwargs)


torch.load = _load


UD_URL = "https://github.com/UniversalDependencies/UD_Turkish-IMST/archive/refs/heads/master.zip"
DATA_DIR = Path("data/ud_tr_imst")
TEST_FILE = DATA_DIR / "UD_Turkish-IMST-master" / "tr_imst-ud-test.conllu"


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


def parse_sentence(lines):
    tokens = []
    for line in lines:
        cols = line.split("\t")
        if len(cols) < 8:
            continue
        tok_id = cols[0]
        if "-" in tok_id or "." in tok_id:
            continue
        tokens.append(
            {
                "id": int(tok_id),
                "form": cols[1],
                "upos": cols[3],
                "head": int(cols[6]),
                "deprel": cols[7],
            }
        )
    return tokens


def main():
    download_ud_treebank()

    if not TEST_FILE.exists():
        raise FileNotFoundError(f"Test file not found: {TEST_FILE}")

    stanza.download("tr", verbose=False)
    nlp = stanza.Pipeline("tr", processors="tokenize,pos,lemma,depparse", tokenize_no_ssplit=False, verbose=False)

    total = 0
    uas = 0
    las = 0

    for sent_lines in iter_conllu_sentences(TEST_FILE):
        gold = parse_sentence(sent_lines)
        if not gold:
            continue
        text = " ".join(tok["form"] for tok in gold)
        doc = nlp(text)
        if not doc.sentences:
            continue
        pred_words = doc.sentences[0].words
        if len(pred_words) != len(gold):
            # Skip sentences where tokenization diverges
            continue

        for g, p in zip(gold, pred_words):
            total += 1
            if p.head == g["head"]:
                uas += 1
                if p.deprel == g["deprel"]:
                    las += 1

    if total == 0:
        print("No comparable tokens found.")
        return

    uas_score = uas / total * 100
    las_score = las / total * 100

    print("UD Turkish IMST (test)")
    print(f"Tokens evaluated: {total}")
    print(f"UAS: {uas_score:.2f}")
    print(f"LAS: {las_score:.2f}")


if __name__ == "__main__":
    main()
