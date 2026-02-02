import stanza

nlp = stanza.Pipeline('tr', verbose=False)
doc = nlp("Ali'nin okuduğu kitap")
sent = doc.sentences[0]

print('Token count:', len(sent.tokens))
print('Word count:', len(sent.words))
print('\nTokens:')
for token in sent.tokens:
    print(f'  {token.id}: "{token.text}"')
    for word in token.words:
        print(f'    → {word.id}: "{word.text}" [{word.upos}]')

print('\nWords:')
for word in sent.words:
    print(f'  {word.id}: "{word.text}" [{word.upos}]')
