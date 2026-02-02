# Changelog - Nominal Domain Preference Detection API

## Son Güncellemeler (Şubat 2026)

### 🎯 Akademik Pozisyonlama İyileştirmeleri

#### 1. Terminoloji Değişiklikleri
**Önceki (sorunlu):**
- ❌ "Hata tespiti" / "POS error detection"
- ❌ "Stanza hatası"
- ❌ "Başarı oranı"

**Yeni (akademik):**
- ✅ "Nominal domain preference tespiti"
- ✅ "Task-driven relabeling suggestion"
- ✅ "Preference detection coverage"

**Rationale:** UD (Universal Dependencies) etiketleri zaten doğrudur. Proje, bu etiketleri "hatalı" olarak değil, discourse/semantic görevler için yetersiz kalabileceği durumları tespit eder.

#### 2. Output Label Değişiklikleri

| Önceki | Yeni | Açıklama |
|--------|------|----------|
| ❌ HATA | ❗ STRONG PREFERENCE | Confidence >0.85 |
| ⚠️ UYARI | ⚠️ WEAK PREFERENCE | Confidence <0.85 |
| ✅ DOĞRU | ✅ UD-UYUMLU | Preference yok |

**Test output örneği:**
```
❗ STRONG PREFERENCE Yazma defteri aldım.
   └─ 1 strong preference (task-driven suggestion):
      • Yazma: Nominal domain preference (VERB-origin) (güven: 90%)
```

### 🔬 Teknik İyileştirmeler

#### 3. Lexicalized Compound Detection (-mA eki)

**Sorun:** "Yüzme havuzu" gibi kalıcılaşmış bileşikler yanlışlıkla preference olarak işaretleniyordu.

**Çözüm:** Whitelist eklendi
```python
LEXICALIZED_mA = [
    'yüzme',   # yüzme havuzu/salonu/sporu
    'koşma',   # koşma parkuru/sporu
    'kayma', 'dolma', 'sarma', 'basma', 'boyama', 'çizme'
]
```

**Sonuç:**
- ✅ "Yüzme havuzu" → NO PREFERENCE (doğru!)
- ❗ "Yazma defteri" → PREFERENCE (doğru!)
- ✅ "Koşma parkuru" → NO PREFERENCE (doğru!)
- ❗ "Okuma kitabı" → PREFERENCE (doğru!)

#### 4. Centering Theory Cb Computation (Tam Cf-based)

**Önceki basitleştirilmiş yöntem:**
```python
# Sadece Cp(U_n-1) kontrol ediliyordu
if Cp(U_n-1) in Cf(U_n):
    Cb = Cp(U_n-1)
```

**Yeni akademik standart (Grosz, Joshi & Weinstein 1995):**
```python
# Tüm Cf(U_n-1) listesi öncelik sırasına göre taranır
for entity in Cf(U_n-1):  # Öncelik sırasına göre
    if entity in Cf(U_n):
        Cb = entity
        break  # İlk bulunan = en yüksek öncelikli
```

**Avantajlar:**
- Söylem geçişleri (Continue, Retain, Shift) daha doğru hesaplanır
- Pro-drop (örtük özne) desteği geliştirildi
- Çok aktörlü diyaloglarda daha iyi performans

### 📊 Metrik Açıklamaları

**Coverage vs Accuracy:**
```
Coverage: 61.1%

NOT: Bu 'POS doğruluğu' değil, 'preference detection coverage'dir.
     UD etiketleri doğrudur; yukarıdakiler discourse görevleri için önerilerdir.
```

- **Coverage:** Diagnostic test set'inde kaç örneğin preference ürettiği
- **NOT accuracy:** UD etiketlerinin doğruluğu değil
- **Purpose:** Discourse görevleri için task-driven önerilerin kapsamı

### 📚 README Güncellemeleri

1. **Başlık:** "Hata Tespiti" → "Nominal Domain Preference Tespiti"
2. **API Örnekleri:** Tüm "hata" referansları "preference" ile değiştirildi
3. **Yeni bölüm:** "Centering Theory İyileştirmesi: Tam Cf-based Cb Computation"
4. **Lexicalized Compound İstisnalar:** Dokümante edildi
5. **Metrik açıklaması:** Coverage vs accuracy farkı vurgulandı

### 🎓 Akademik Çerçeve

**UD'ye saygı:**
- UD etiketleri **doğrudur** ve standarda uygundur
- `-DIK`, `-mA`, `-mAk` formlarının VERB etiketlenmesi **meşrudur**
- VerbForm=Part/Vnoun özellikleri UD'de tutarlıdır

**Projenin katkısı:**
- Discourse/semantic görevler için **complementary** analiz
- Coreference, centering, semantic role labeling için öneriler
- UD'ye **alternatif değil**, **ek katman**

### 🔄 Backward Compatibility

**API değişiklikleri minimal:**
- Fonksiyon isimleri aynı (`detect_minimalist_errors`)
- Return format aynı (`total_errors`, `errors`)
- Sadece `type` field içeriği güncellendi:
  - Önceki: "NOUN_VERB_CONFUSION"
  - Yeni: "Nominal domain preference (VERB-origin)"

**Migration:** Kod değişikliği gerekmez, sadece output display güncellenebilir.

### ✅ Test Coverage

**18 test senaryosu:**
- -DIK eki: 3 test
- -mA eki: 3 test (lexicalized compound aware)
- -mAk eki: 3 test
- -Iş eki: 3 test (UD-uyumlu)
- Adlaşmış sıfatlar: 3 test
- UD-uyumlu: 3 test

**7 preference tespit edildi:**
- Coverage: 61.1%
- Strong preference: 6
- Weak preference: 1

### 🚀 Gelecek İyileştirmeler

1. **Daha zengin lexicalized compound listesi**
2. **Context-aware preference scoring** (cümle bağlamına göre)
3. **Multi-word expression (MWE) desteği**
4. **Discourse relation annotation** (RST, PDTB)
5. **Fine-tuning için annotated dataset**

---

**Sonuç:** Proje artık akademik standartlara uygun, UD'ye saygılı ve discourse görevleri için değerli öneriler sunan bir araç konumunda.
