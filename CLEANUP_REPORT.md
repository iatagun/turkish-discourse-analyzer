# PROJE DOSYA TEMİZLİK RAPORU

## 📋 KULLANILMAYAN DOSYALAR (SİLİNEBİLİR)

### Root - Debug Scripts (Geçici test dosyaları)
- ❌ `debug_mwt.py` - MWT token testi (artık gerekli değil)
- ❌ `debug_specificity.py` - Özgüllük debug testi (geçici)
- ❌ `debug_stanza_feats.py` - FEATS debug testi (geçici)

### Evaluation - Eski Test/Değerlendirme Dosyaları
- ❌ `evaluation/evaluate_ud_tr.py` - Eski UD değerlendirme
- ❌ `evaluation/evaluate_ud_tr_rerank.py` - Eski rerank değerlendirme
- ❌ `evaluation/optimize_centering.py` - Centering optimizasyonu (kullanılmıyor)
- ❌ `evaluation/test_ambiguity_types.py` - Belirsizlik testi (eski)
- ❌ `evaluation/test_centering_turkish.py` - Eski centering testi

### Error Detection - Eski Test Dosyaları
- ❌ `error_detection/evaluate_pos_centering.py` - Eski POS/centering değerlendirme
- ❌ `error_detection/test_minimalist_vs_stanza.py` - Karşılaştırma testi (eski)
- ❌ `error_detection/test_pos_error_centering.py` - Eski entegrasyon testi
- ❌ `error_detection/tr_pos_test.py` - Eski POS testi

### Core - Kullanılmayan Modüller
- ⚠️ `core/demo_stanza_centering.py` - Demo (kullanılmıyor ama öğretici olabilir)
- ⚠️ `core/turkish_centering_theory.py` - Centering theory (şu an aktif değil)

### API - Gereksiz Dosyalar
- ❌ `api/example.py` - Eski örnek (simple_check.py ve enhanced_analysis.py var)
- ❌ `api/quick_example.py` - Hızlı örnek (comprehensive_test.py daha iyi)
- ⚠️ `api/CHANGELOG.md` - Değişiklik logu (tutulabilir)
- ⚠️ `api/README.md` - API dökümantasyonu (tutulabilir)

---

## ✅ KULLANILAN DOSYALAR (TUTULACAK)

### Core Modules
- ✅ `src/propositional_semantics.py` - Ana semantik modül
- ✅ `error_detection/minimalist_pos_error_detection.py` - Ana POS detection

### API Files
- ✅ `api/main.py` - Ana API
- ✅ `api/simple_check.py` - Basit kontrol API
- ✅ `api/enhanced_analysis.py` - Gelişmiş analiz API
- ✅ `api/test_lexicalized.py` - Lexicalized test (çalışıyor)

### Test Files
- ✅ `comprehensive_test.py` - Ana kapsamlı test
- ✅ `test_semantic_integration.py` - Semantik entegrasyon testi
- ✅ `test_minimalist_fixes.py` - Minimalist fix testi

### Documentation
- ✅ `docs/GELISMIS_ORNEK_ANALIZ.md` - Gelişmiş analiz dökümantasyonu
- ✅ `docs/PROPOSITIONAL_SEMANTICS_INTEGRATION.md` - Semantik entegrasyon dökümantasyonu
- ✅ `README.md` - Ana README

### Configuration
- ✅ `.gitignore`
- ✅ `LICENSE`
- ✅ `api/requirements.txt`

---

## 📊 İSTATİSTİKLER

- **Silinebilir dosyalar**: 14 dosya
- **Tutulacak dosyalar**: 12 dosya
- **Opsiyonel dosyalar**: 4 dosya (demo, centering theory, docs)

---

## 🎯 ÖNERİLEN AKSIYONLAR

### 1. HEMEN SİL (Gereksiz/Debug Dosyaları)
```bash
# Root debug scripts
rm debug_mwt.py debug_specificity.py debug_stanza_feats.py

# Evaluation klasörü (tamamını)
rm -r evaluation/

# Error detection eski testler
rm error_detection/evaluate_pos_centering.py
rm error_detection/test_minimalist_vs_stanza.py
rm error_detection/test_pos_error_centering.py
rm error_detection/tr_pos_test.py

# API eski örnekler
rm api/example.py api/quick_example.py
```

### 2. KARAR VER (İhtiyaca Göre)
- `core/` klasörü: Centering theory şu an kullanılmıyor
  - **Seçenek A**: Sil (POS tagging odaklıyız)
  - **Seçenek B**: Tut (gelecekte kullanılabilir)

### 3. REORGANIZE ET
Şu yapı önerilir:
```
centering_test/
├── src/
│   ├── propositional_semantics.py
│   └── pos_error_detection.py (minimalist_pos_error_detection.py → rename)
├── api/
│   ├── main.py
│   ├── simple_check.py
│   └── enhanced_analysis.py
├── tests/
│   ├── test_comprehensive.py (comprehensive_test.py → move)
│   ├── test_semantic_integration.py (move)
│   ├── test_minimalist.py (test_minimalist_fixes.py → rename)
│   └── test_lexicalized.py (api/test_lexicalized.py → move)
├── docs/
│   ├── GELISMIS_ORNEK_ANALIZ.md
│   └── PROPOSITIONAL_SEMANTICS_INTEGRATION.md
└── README.md
```
