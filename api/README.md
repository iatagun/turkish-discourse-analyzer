# Türkçe POS Tagging - Nominal Domain Preference Tespiti - Python API

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

**Metrikler:**
- Test sonuçlarındaki "coverage" = **preference detection kapsamı** (diagnostic test set üzerinde)
- Bu **POS tagging accuracy DEĞİLDİR**
- UD etiketleri zaten doğrudur; metrik sadece discourse görevleri için önerileri ölçer

## Kurulum

Ek bağımlılık yok. Ana proje bağımlılıkları yeterli.

## Kullanım

### 1. Minimalist Program ile Nominal Domain Preference Tespiti

```python
from api.main import detect_minimalist_errors

# Kelime listesi hazırla
words = [
    {"text": "okuduğu", "pos": "VERB", "morphology": ["-DIK"]},
    {"text": "kitap", "pos": "NOUN", "morphology": []}
]

# Analiz et
result = detect_minimalist_errors(words)

print(f"Toplam preference: {result['total_errors']}")
for error in result['errors']:
    print(f"- {error['word']}: {error['reason']} (güven: {error['confidence']})")
```

**Çıktı:**
```
Toplam preference: 1
- okuduğu: Nominal domain preference (VERB-origin) (güven: 0.9)
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
print(f"Discourse issues: {len(result['errors'])}")
```

**Çıktı:**
```
Söylem skoru: 4.0
Geçişler: ['CONTINUE']
Discourse issues: 0
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
    print(f"Preferences: {result['total_errors']}")
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

Nominal domain preferences tespit eder. Fonksiyon adı "errors" içerse de, bunlar **UD hataları DEĞİL**, discourse görevleri için task-driven önerilerdir.

**Parametreler:**
- `words` (List[Dict]): Kelime listesi
  - `text` (str): Kelime metni
  - `pos` (str): POS etiketi (NOUN, VERB, ADJ, vb.)
  - `morphology` (List[str], opsiyonel): Morfolojik özellikler
  - `feats` (str, opsiyonel): FEATS bilgisi (finit fiil kontrolü için)

**Dönüş:**
```python
{
    "total_errors": int,  # NOT: "errors" = preference sayısı (backward compatibility)
    "errors": [  # Her bir preference
        {
            "word": str,
            "type": str,  # "Nominal domain preference (VERB-origin)" vb.
            "found_pos": str,  # UD'nin verdiği etiket (doğru)
            "expected_pos": str,  # Discourse görevleri için öneri
            "reason": str,
            "confidence": float  # 0.0-1.0 (>0.85: strong, <0.85: weak)
        }
    ]
}
```

**Lexicalized Compound İstisnalar:**
- `-mA` eki için: "yüzme", "koşma", "kayma", "dolma", "sarma" gibi kalıcılaşmış bileşikler preference üretmez
- Örnek: "Yüzme havuzu" → preference YOK, "Yazma defteri" → preference VAR
```

### `detect_centering_errors(sentences)`

Merkezleme Kuramı (Centering Theory) ile söylem tutarlılığı analizi. **Backward Center (Cb)** hesabı **tam Cf-based** yöntemle yapılır (Grosz, Joshi & Weinstein 1995).

**Parametreler:**
- `sentences` (List[Dict]): Cümle listesi
  - `text` (str): Cümle metni
  - `words` (List[Dict]): Kelime listesi
    - `text` (str): Kelime
    - `pos` (str): POS etiketi
    - `dependency` (str): Bağımlılık rolü (nsubj, obj, vb.)

**Dönüş:**
```python
{
    "discourse_score": float,  # 0.0-4.0 (yüksek = tutarlı söylem)
    "transitions": List[str],  # ['Continue', 'Retain', 'Smooth-Shift', 'Rough-Shift']
    "errors": [  # Söylem tutarsızlıkları (UD hataları DEĞİL)
        {
            "sentence_index": int,
            "transition": str,
            "score": int,
            "severity": str  # high (Rough-Shift), medium, low
        }
    ]
}
```

**Centering İyileştirmeleri:**
- ✅ Zamir çözümleme: "O" → önceki Cp'ye resolve edilir
- ✅ Örtük özne (pro-drop) desteği
- ✅ DET→PRON discourse-driven relabeling (aşağıya bakın)
- ✅ Tam Cf-based Cb: Tüm Cf(U_n-1) listesi öncelik sırasına göre taranır
```

## Discourse-Driven Relabeling (DET ↔ PRON)

### Centering Theory İyileştirmesi: Tam Cf-based Cb Computation

**Akademik tanım (Grosz, Joshi & Weinstein 1995):**
> Cb(U_n) = en yüksek öncelikli Cf(U_n-1) elemanı ki Cf(U_n)'de realize olmuş

**Önceki basitleştirilmiş yöntem (HATALI):**
- Sadece `Cp(U_n-1)` kontrol ediliyordu
- Eğer Cp şu anki cümlede varsa → Cb

**Yeni tam yöntem (DOĞRU):**
- Tüm `Cf(U_n-1)` listesi en yüksek öncelikten en düşüğe doğru taranır
- İlk realize olmuş (şu anki cümlede bulunan) entity → Cb
- Örtük özne (pro-drop) durumu da kontrol edilir

Bu iyileştirme, söylem geçişlerinin (Continue, Retain, Shift) daha doğru hesaplanmasını sağlar.

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


