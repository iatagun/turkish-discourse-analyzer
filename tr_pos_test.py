import torch


# Work around PyTorch 2.6+ defaulting to weights_only=True in torch.load
_orig_load = torch.load

def _load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_load(*args, **kwargs)


torch.load = _load

import spacy_stanza

text = "Bugün İstanbul'da hava çok güzel ama biraz rüzgarlı."

nlp = spacy_stanza.load_pipeline("tr")
doc = nlp(text)

print("TEXT:", text)
print("TOKENS:")
for token in doc:
    print(f"{token.text}\t{token.pos_}\t{token.tag_}")
