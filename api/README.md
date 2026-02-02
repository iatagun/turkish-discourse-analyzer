# Türkçe POS Tagging Hata Tespiti - Python API

Basit Python fonksiyonları ile iki farklı dilbilimsel yaklaşım:
1. **Minimalist Program** - Nominal domain preferences (adlaşma eğilimleri)
2. **Merkezleme Kuramı** - Söylem tutarlılığı (discourse coherence)

## Önemli Not: UD vs. Görev-Odaklı Etiketleme

Bu proje **UD (Universal Dependencies) etiketlerini "hata" olarak değil**, 
**discourse/semantic görevler için yetersiz kalabileceği durumları** tespit eder.

- UD'de `-DIK`, `-mA`, `-mAk` gibi türetimler sıklıkla VERB/ADJ olarak kalır (VerbForm=Part/Vnoun)
- Bu UD açısından **doğrudur** ve standarda uygundur
- Ancak **coreference, centering, semantic role** gibi görevlerde nominal davranış gösterebilirler
- Proje bu tür "**nominal domain preference**" durumlarını tespit eder

**Terminoloji:**
- ❌ "Stanza hatası" DEMİYORUZ
- ✅ "Nominal domain shift / preference" DİYORUZ
- ✅ "Task-driven relabeling suggestion" DİYORUZ

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

## Discourse-Driven Relabeling (DET ↔ PRON)

### Neden "O" Bazı Durumlarda DET, Bazılarında PRON?

**UD perspektifi:**
- "O kitap" → `O[DET] kitap[NOUN]` (determiner/işaret sıfatı)
- "O geldi" → `O[PRON] geldi[VERB]` (zamir/özne)

**Bu UD açısından DOĞRU!** Ancak **discourse görevleri** (coreference, centering) için yetersiz:

```python
# Örnek discourse:
Cümle 1: "Ahmet markete gitti."
Cümle 2: "O süt aldı."  # UD: O[DET] süt[NOUN]
```

**Sorun:** UD'de "O" DET etiketlenmiş, ama **discourse-level anlamda Ahmet'e refer ediyor**.

**Proje çözümü:**
1. Centering Theory'nin **backward center (Cb)** hesabı için "O"yu `PRON` olarak treat et
2. Önceki cümledeki `Cp(U_n-1)`'i bul (örn: "Ahmet")
3. "O"yu resolve et: `O → Ahmet`

### Kod Örnekleri

**DET→PRON Relabeling (Discourse Context):**
```python
# Cümle 2'de "O" UD'de DET ama discourse'da PRON:
{
    "text": "O süt aldı.",
    "words": [
        {"text": "O", "pos": "DET"},  # UD etiketlenmesi
        {"text": "süt", "pos": "NOUN"},
        {"text": "aldı", "pos": "VERB"}
    ]
}

# Centering Theory analizi:
# 1. Önceki Cp = "Ahmet"
# 2. "O" discourse'da Ahmet'e refer ediyor
# 3. İşleme sırasında: O → PRON (discourse role) ve resolve et → "Ahmet"
```

**PRON Handling (Zaten Doğru):**
```python
# Cümle'de "O" zaten özne:
{
    "text": "O geldi.",
    "words": [
        {"text": "O", "pos": "PRON"}  # UD doğru
    ]
}
# Bu durumda relabeling gerekmez, direkt resolve edilir
```

### Akademik Çerçeveleme

**NOT:** Bu projede **DET→PRON relabeling**, UD'nin "hatalı" olduğu anlamına GELMİYOR!

- **UD doğru:** "O kitap" yapısında "O" gerçekten determiner
- **Discourse doğru:** Aynı "O", discourse-level'da önceki entity'ye refer ediyor

**İki seviyeli analiz:**
1. **Syntactic (UD):** "O" = DET (işaret sıfatı)
2. **Discourse (Centering):** "O" = anaphoric reference → PRON muamelesi

Proje, **discourse görevleri için** syntax-level etiketleri **temporarily remap** ediyor.
Bu, UD'ye **alternatif** değil, **complementary** bir yaklaşımdır.

### Hangi Durumlarda Relabeling Yapılır?

**Trigger koşulları:**
1. Token "O", "bu", "şu" gibi demonstrative
2. UD etiketi `DET`
3. **Discourse context mevcut** (önceki cümle var)
4. Önceki `Cp` ile semantik bağlantı olası

**Relabeling YAPILMAZ:**
- Discourse yoksa (ilk cümle)
- "O" özne pozisyonunda değilse ve önceki Cp ile match etmiyorsa
- Önceki Cp yoksa veya resolve edilemiyorsa


