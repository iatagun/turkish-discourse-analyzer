# Türkçe POS Tagging Hata Tespiti - Python API

Basit Python fonksiyonları ile iki farklı dilbilimsel yaklaşım:
1. **Minimalist Program** - Nominal türetmeler, adlaşmış sıfatlar
2. **Merkezleme Kuramı** - Söylem tutarlılığı

## Kurulum

Ek bağımlılık yok. Ana proje bağımlılıkları yeterli.

## Kullanım

### 1. Minimalist Program ile Hata Tespiti

```python
from api.main import detect_minimalist_errors

# Kelime listesi hazırla
words = [
    {"text": "okuduğu", "pos": "VERB", "morphology": ["-DIK"]},
    {"text": "kitap", "pos": "NOUN", "morphology": []}
]

# Analiz et
result = detect_minimalist_errors(words)

print(f"Toplam hata: {result['total_errors']}")
for error in result['errors']:
    print(f"- {error['word']}: {error['reason']} (güven: {error['confidence']})")
```

**Çıktı:**
```
Toplam hata: 1
- okuduğu: Nominal suffix '-DIK' detected, should be NOUN (güven: 0.9)
```

### 2. Merkezleme Kuramı ile Söylem Analizi

```python
from api.main import detect_centering_errors

# Cümle listesi hazırla
sentences = [
    {
        "text": "Ahmet markete gitti.",
        "words": [
            {"text": "Ahmet", "pos": "PROPN", "dependency": "nsubj"},
            {"text": "markete", "pos": "NOUN", "dependency": "obl"},
            {"text": "gitti", "pos": "VERB", "dependency": "root"}
        ]
    },
    {
        "text": "O süt aldı.",
        "words": [
            {"text": "O", "pos": "PRON", "dependency": "nsubj"},
            {"text": "süt", "pos": "NOUN", "dependency": "obj"},
            {"text": "aldı", "pos": "VERB", "dependency": "root"}
        ]
    }
]

# Analiz et
result = detect_centering_errors(sentences)

print(f"Söylem skoru: {result['discourse_score']}")
print(f"Geçişler: {result['transitions']}")
print(f"Hatalar: {len(result['errors'])}")
```

**Çıktı:**
```
Söylem skoru: 4.0
Geçişler: ['CONTINUE']
Hatalar: 0
```

### 3. Komple Örnek (Her İki Yaklaşım)

```python
from api.main import detect_minimalist_errors, detect_centering_errors

# Test cümleleri
test_data = [
    {
        "text": "Ali'nin okuduğu kitap burada.",
        "words": [
            {"text": "Ali'nin", "pos": "PROPN", "morphology": ["-in"]},
            {"text": "okuduğu", "pos": "VERB", "morphology": ["-DIK"]},
            {"text": "kitap", "pos": "NOUN", "morphology": []},
            {"text": "burada", "pos": "ADV", "morphology": []}
        ]
    },
    {
        "text": "Onu yarın okuyacak.",
        "words": [
            {"text": "Onu", "pos": "PRON", "dependency": "obj"},
            {"text": "yarın", "pos": "NOUN", "dependency": "obl"},
            {"text": "okuyacak", "pos": "VERB", "dependency": "root"}
        ]
    }
]

# Minimalist analiz (her cümle için)
print("=== MİNİMALİST PROGRAM ===")
for sent in test_data:
    result = detect_minimalist_errors(sent["words"])
    print(f"\nCümle: {sent['text']}")
    print(f"Hatalar: {result['total_errors']}")
    for err in result['errors']:
        print(f"  - {err['word']}: {err['type']} ({err['confidence']})")

# Centering analiz (söylem tutarlılığı)
print("\n=== MERKEZLEME KURAMI ===")
centering_result = detect_centering_errors(test_data)
print(f"Söylem Skoru: {centering_result['discourse_score']}")
print(f"Geçişler: {centering_result['transitions']}")
```

## API Referansı

### `detect_minimalist_errors(words)`

**Parametreler:**
- `words` (List[Dict]): Kelime listesi
  - `text` (str): Kelime metni
  - `pos` (str): POS etiketi (NOUN, VERB, ADJ, vb.)
  - `morphology` (List[str], opsiyonel): Morfolojik özellikler

**Dönüş:**
```python
{
    "total_errors": int,
    "errors": [
        {
            "word": str,
            "type": str,  # NOUN_VERB_CONFUSION, ADJ_NOUN_CONFUSION, vb.
            "found_pos": str,
            "expected_pos": str,
            "reason": str,
            "confidence": float  # 0.0-1.0
        }
    ]
}
```

### `detect_centering_errors(sentences)`

**Parametreler:**
- `sentences` (List[Dict]): Cümle listesi
  - `text` (str): Cümle metni
  - `words` (List[Dict]): Kelime listesi
    - `text` (str): Kelime
    - `pos` (str): POS etiketi
    - `dependency` (str): Bağımlılık rolü

**Dönüş:**
```python
{
    "discourse_score": float,  # Yüksek = tutarlı
    "transitions": List[str],  # CONTINUE, RETAIN, vb.
    "errors": [
        {
            "sentence_index": int,
            "transition": str,
            "score": int,
            "severity": str  # high, medium, low
        }
    ]
}
```
