# Önermesel Semantik Entegrasyon Planı

## 🎯 Verdiğin Teorinin Projeye Uygulanması

### Tespit Edilen Bağlantılar:

#### 1. **-DIK Eki → Parçalı Yüklem → Özgüllük**

**Teorin:**
> "-DIK eki parçalı yüklem oluşturur → +özgül, +varoluş, +belirli"

**Kod:**
```python
# error_detection/minimalist_pos_error_detection.py

# ŞU ANKİ KOD:
if '-DIK' in item.morphology and item.pos == 'VERB':
    return {
        'type': POSErrorType.NOUN_VERB_CONFUSION,
        'reason': 'Nominal suffix detected'
    }

# TEORİK ZENGİNLEŞTİRME:
if '-DIK' in item.morphology and item.pos == 'VERB':
    # -DIK eki:
    # 1. Parçalı yüklem marker'ı
    # 2. Özgüllük kazandırır (+specific)
    # 3. Varoluş değeri verir (+existential)
    # 4. Nominal domain'e çeker
    return {
        'type': POSErrorType.NOUN_VERB_CONFUSION,
        'reason': 'Parçalı yüklem → nominal domain (özgüllük)',
        'semantic_features': {
            'predicate_type': 'parçalı',
            'specific': True,
            'existential': True,
            'proposition_type': 'synthetic'
        }
    }
```

#### 2. **Aorist (-Ar/-Ir) → Bütüncül Yüklem → Generic**

**Teorin:**
> "Geniş zaman (aorist) bütüncül yüklem → generic encoding, özellik tümcesi"

**Örnek:**
- "Ali sabahları erken **kalkar**" → Bütüncül, özellik
- "Ali dün erken **kalktı**" → Parçalı, olay

**Kod entegrasyonu:**
```python
def analyze_predicate_aspectuality(feats: str) -> Dict:
    """
    Yüklemin özellik/olay ayrımı
    
    Bütüncül (özellik): Tense=Aor, Aspect=Hab
    Parçalı (olay): Tense=Past, Tense=Fut, Aspect=Prog
    """
    if 'Tense=Aor' in feats or 'Aspect=Hab' in feats:
        return {
            'predicate_type': 'bütüncül',
            'sentence_type': 'özellik',
            'generic': True,
            'time_bound': False
        }
    elif any(t in feats for t in ['Tense=Past', 'Tense=Fut', 'Aspect=Prog']):
        return {
            'predicate_type': 'parçalı',
            'sentence_type': 'olay',
            'generic': False,
            'time_bound': True
        }
```

#### 3. **Case Marking → Özgüllük & Belirlilik**

**Teorin:**
> "Belirtme hali (-I) morfolojik belirlilik verir → +özgül, +belirli"

**Örnekler:**
- "**kapıyı** açmak" (accusative) → +özgül, +belirli (morfolojik), -belirli (anlamsal: alıcı bilmiyor)
- "**bir kızı** seveceğim" → +özgül (morfolojik), -belirli (anlamsal), -varoluş (varsayımsal)

**Kod:**
```python
def analyze_definiteness(word: str, feats: str, context: str) -> Dict:
    """
    Belirlilik analizi (morfolojik vs anlamsal)
    
    Morfolojik belirlilik: Case=Acc, Definite=Def
    Anlamsal belirlilik: Alıcı için kimliklendirme
    """
    morphologically_definite = 'Case=Acc' in feats
    
    # Anlamsal belirlilik context'e bağlı
    # "bir kızı" → morfolojik +, anlamsal -
    # "bu kızı" → morfolojik +, anlamsal +
    semantically_definite = word.lower() in ['bu', 'şu', 'o']
    
    return {
        'morphologically_definite': morphologically_definite,
        'semantically_definite': semantically_definite,
        'specific': morphologically_definite or semantically_definite,
        'note': 'Belirlilik alıcı perspektifinden değerlendirilir'
    }
```

#### 4. **Determiner Analysis → "bir" vs "bu/şu/o"**

**Teorin:**
> "bir kız" → +özgül, -belirli (alıcı için)  
> "bu kız" → +özgül, +belirli

**Centering Theory bağlantısı:**
```python
# Şu anki DET→PRON relabeling mantığı genişletilebilir:

if word.text.lower() == 'o' and word.pos == 'DET':
    # "O" hem özgüllük hem belirlilik marker'ı
    # Discourse'da önceki Cp'ye refer ediyorsa:
    # → +özgül, +belirli, +anaphoric
    
    # Teorik açıklama:
    # DET olarak: +belirli (bu nesneyi tanımlıyor)
    # PRON olarak: +özgül, +anaphoric (öncekine refer)
```

---

## 📊 Önerilen Yeni Modüller

### Modül 1: `specificity_analyzer.py`
```python
class SpecificityAnalyzer:
    """Özgüllük ve belirlilik analizi"""
    
    def analyze_noun_phrase(self, words: List[Word]) -> SemanticFeatures:
        """
        Ad öbeğinin özgüllük özellikleri
        
        +özgül: Özel ad, accusative, demonstrative
        +belirli: Alıcı için kimliklendirme mümkün
        +varoluş: Discourse'da refer edilen varlık
        """
        pass
```

### Modül 2: `proposition_analyzer.py`  
```python
class PropositionAnalyzer:
    """Önermesel değer hesaplama"""
    
    def classify_proposition_type(self, sentence: Sentence) -> PropositionType:
        """
        Analitik vs Sentetik önerme
        
        Analitik: Bütüncül yüklem + generic subject
        Sentetik: Parçalı yüklem veya özgül subject
        """
        pass
```

### Modül 3: `predicate_classifier.py`
```python
class PredicateClassifier:
    """Yüklem tipi sınıflandırma"""
    
    def classify_predicate(self, verb: Word) -> PredicateType:
        """
        Bütüncül vs Parçalı yüklem
        
        Bütüncül: Aorist, Habitual → Özellik tümcesi
        Parçalı: Past, Future, Progressive → Olay tümcesi
        """
        pass
```

---

## 🔗 Mevcut Sistemle Entegrasyon

### `api/main.py` Güncellemesi:

```python
from src.propositional_semantics import TurkishPropositionAnalyzer

def check_sentence_with_semantics(sentence: str) -> Dict:
    """
    Cümle kontrolü + önermesel semantik analizi
    
    Returns:
        {
            'pos_preferences': [...],      # Mevcut nominal domain
            'propositional_value': {       # YENİ!
                'proposition_type': 'analytic' | 'synthetic',
                'predicate_type': 'bütüncül' | 'parçalı',
                'semantic_features': {
                    'specific': bool,
                    'definite': bool,
                    'existential': bool
                }
            }
        }
    """
    # Mevcut POS tagging
    result = check_sentence(sentence)
    
    # Önermesel analiz ekle
    prop_analyzer = TurkishPropositionAnalyzer()
    # ... implementation
    
    return result
```

---

## 💡 Pratik Kullanım Örnekleri

### Örnek 1: Generic vs Specific Detection

```python
>>> analyze("Kuşlar uçar")
{
    'proposition': 'analytic',
    'predicate': 'bütüncül',
    'generic': True,
    'explanation': 'Genel-geçer özellik tümcesi'
}

>>> analyze("Kuşlar uçtu")  
{
    'proposition': 'synthetic',
    'predicate': 'parçalı',
    'generic': False,
    'explanation': 'Zamana gönderimli olay tümcesi'
}
```

### Örnek 2: Definiteness Tracking

```python
>>> analyze("Bir kız tanıdım günde iki paket sigara içer")
{
    'subject': {
        'text': 'Bir kız',
        'specific': True,           # +özgül
        'definite': False,          # -belirli (alıcı için)
        'existential': True         # +varoluş (konuşucu için)
    },
    'predicate': {
        'text': 'içer',
        'type': 'bütüncül',         # Özellik
        'tense': 'aorist'
    }
}
```

---

## 🎯 Sonuç: Bu Teorinin Projeye Katkısı

**Şu anki durum:** POS tagging hataları tespit ediliyor ama **WHY?** sorusu cevaplanmıyor.

**Senin teorinle:** 
✅ **WHY** sorusuna cevap var!
- "-DIK eki neden NOUN'a çekiyor?" → Parçalı yüklem, özgüllük kazandırıyor
- "Aorist neden generic?" → Bütüncül yüklem, zamanda noktaya oturmuyor
- "Accusative neden özgüllük marker'ı?" → Morfolojik belirlilik

✅ **Centering Theory ile uyum:**
- Özgüllük → Cb/Cp hesabında öncelik
- Belirlilik → Anaphora resolution
- Varoluş → Discourse referent tracking

✅ **Akademik savunulabilirlik:**
- "Random POS preference" değil
- "Önermesel semantik temelli preference" 🎓
