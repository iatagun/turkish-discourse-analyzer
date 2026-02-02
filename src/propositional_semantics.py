"""
Propositional Semantics Analysis for Turkish

Bu modül Türkçe tümcelerin önermesel değerini analiz eder:
- Analitik vs Sentetik önermeler
- Bütüncül vs Parçalı yüklemler  
- Özgüllük (specificity) ve Belirlilik (definiteness)
- Varoluş (existential) değeri

Teorik Temel:
- Analitik Önerme: Mutlak doğru/yanlış, bütüncül yüklem, genel-geçer
  Örnek: "Kuşlar uçar" (generic, özellik tümcesi)
  
- Sentetik Önerme: +/- doğruluk değeri, parçalı yüklem, zamana gönderimli
  Örnek: "Kuşlar uçtu" (specific, olay tümcesi)

Önermesel Değer Hesabı:
- Doğrulanabilirlik (verifiability)
- Yanlışlanabilirlik (falsifiability)
- Bildirim değeri (assertive value)
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any

# Module-level cache for Stanza pipeline to avoid attaching attributes to functions
_stanza_nlp: Optional[Any] = None


class PropositionType(Enum):
    """Önerme tipi"""
    ANALYTIC = "analytic"      # Analitik önerme (genel-geçer)
    SYNTHETIC = "synthetic"    # Sentetik önerme (zamana gönderimli)
    NON_PROPOSITIONAL = "non_propositional"  # Önerme değil (soru, dilek, vb.)


class PredicateType(Enum):
    """Yüklem tipi"""
    HOLISTIC = "bütüncül"      # Bütüncül yüklem (zamanda noktaya oturmaz)
    PARTITIVE = "parçalı"      # Parçalı yüklem (zamanda noktaya oturur)


class SentenceType(Enum):
    """Tümce tipi"""
    PROPERTY = "özellik"       # Özellik tümcesi (analitik)
    EVENT = "olay"             # Olay tümcesi (sentetik)
    HABITUAL = "alışkanlık"    # Alışkanlık tümcesi (sentetik)
    QUESTION = "soru"
    REQUEST = "istek"
    EXCLAMATION = "hayret"


@dataclass
class SemanticFeatures:
    """Anlamsal özellikler"""
    specific: bool              # +özgül / -özgül (generic)
    existential: bool           # +varoluş / -varoluş
    definite: bool              # +belirli / -belirli (alıcı için)
    singular: bool              # +tekil / +çoğul
    
    # Morphosyntactic vs Semantic definiteness
    morphologically_definite: bool   # Morfolojik belirlilik (accusative, vb.)
    semantically_definite: bool      # Anlamsal belirlilik (alıcı için kimliklendirme)


@dataclass
class PropositionalValue:
    """Önermesel değer"""
    proposition_type: PropositionType
    predicate_type: PredicateType
    sentence_type: SentenceType
    
    # Doğruluk değerleri
    verifiable: float           # Doğrulanabilirlik (0.0-1.0)
    falsifiable: float          # Yanlışlanabilirlik (0.0-1.0)
    assertive_value: float      # Bildirim değeri
    
    # Özellikler
    time_bound: bool            # Zamana bağlı mı?
    generic: bool               # Generic encoding?
    
    explanation: str


class TurkishPropositionAnalyzer:
    """
    Türkçe tümcelerin önermesel analizi
    
    Örnekler:
    >>> analyzer = TurkishPropositionAnalyzer()
    
    # Analitik önerme
    >>> result = analyzer.analyze("Kuşlar uçar")
    >>> result.proposition_type == PropositionType.ANALYTIC  # True
    >>> result.predicate_type == PredicateType.HOLISTIC      # True
    
    # Sentetik önerme  
    >>> result = analyzer.analyze("Kuşlar uçtu")
    >>> result.proposition_type == PropositionType.SYNTHETIC  # True
    >>> result.predicate_type == PredicateType.PARTITIVE      # True
    """
    
    # Bütüncül yüklem marker'ları (aorist, generic)
    # NOT: Stanza Turkish'te Aorist = 'Aspect=Hab|Tense=Pres' olarak etiketleniyor!
    HOLISTIC_MARKERS = [
        'VerbForm=Vnoun',   # -mA, -mAk (verbal noun)
        'Aspect=Hab',       # Habitual/Aorist (-Ar/-Ir): "kuşlar uçar"
        'VerbForm=Part',    # Participle: "koşan adam"
    ]
    
    # Parçalı yüklem marker'ları (tense-bound)
    # UYARI: 'Tense=Pres' KALDIRILIYOR - Aspect=Hab ile çakışıyor!
    PARTITIVE_MARKERS = [
        'Tense=Past',       # Geçmiş zaman: "kuşlar uçtu"
        'Tense=Fut',        # Gelecek zaman: "kuşlar uçacak"
        'Aspect=Prog',      # Progressive (-Iyor): "kuşlar uçuyor"
        'Aspect=Perf',      # Perfective (Dİ'li geçmiş)
    ]
    
    # Özgüllük marker'ları
    SPECIFICITY_MARKERS = [
        'Case=Acc',         # Belirtme hali (-I/-(y)I)
        'Definite=Def',     # Tanımlık
        'PronType=Dem',     # İşaret zamiri (bu, şu, o)
    ]
    
    def analyze_predicate_type(self, verb_feats: str) -> PredicateType:
        """
        Yüklem tipini belirle
        
        Bütüncül yüklem: Zamanda bir noktaya oturmaz, genel-geçer
        Örnek: "Ali sabahları erken kalkar" (özellik)
        
        Parçalı yüklem: Zamanda bir noktaya oturur, özgül
        Örnek: "Ali dün erken kalktı" (olay)
        """
        feats_lower = verb_feats.lower() if verb_feats else ""
        
        # Parçalı yüklem kontrol (öncelik: zaman belirtici)
        for marker in self.PARTITIVE_MARKERS:
            if marker.lower() in feats_lower:
                return PredicateType.PARTITIVE
        
        # Bütüncül yüklem kontrol
        for marker in self.HOLISTIC_MARKERS:
            if marker.lower() in feats_lower:
                return PredicateType.HOLISTIC
        
        # Default: Belirsiz
        return PredicateType.HOLISTIC  # Conservative
    
    def analyze_specificity(self, noun_feats: str, word: str, upos: str = "") -> SemanticFeatures:
        """
        Özgüllük ve belirlilik analizi
        
        Örnekler:
        - "bir kız" → +özgül, -belirli (alıcı için kimliklendirme yok)
        - "bu kız" → +özgül, +belirli
        - "kapıyı" (acc) → +özgül, +belirli (morfolojik ve anlamsal)
        - "Kuşlar uçar" → -özgül (bare plural = generic)
        """
        feats_lower = noun_feats.lower() if noun_feats else ""
        word_lower = word.lower()
        
        # Özgüllük
        specific = False
        for marker in self.SPECIFICITY_MARKERS:
            if marker.lower() in feats_lower:
                specific = True
                break
        
        # Özel adlar → özgül (UPOS=PROPN ile kontrol et, büyük harf heuristic KALDIRILDI)
        if upos == 'PROPN':
            specific = True
        
        # İşaret sıfatları
        if word_lower in ['bu', 'şu', 'o']:
            specific = True
        
        # ⚡ BARE PLURAL RULE: "Kuşlar uçar" → -özgül (GENERIC)
        # Çoğul + Yalın hal (Nominative) → Generic reference
        is_bare_plural = (
            'number=plur' in feats_lower and 
            'case=nom' in feats_lower and
            not specific  # Zaten demonstrative vs ile işaretlenmemişse
        )
        if is_bare_plural:
            specific = False
        
        # Belirlilik (morfolojik)
        morphologically_definite = 'case=acc' in feats_lower
        
        # Belirlilik (anlamsal) - basit yaklaşım
        # "bir" → -belirli, "bu/şu/o" → +belirli
        semantically_definite = word_lower in ['bu', 'şu', 'o']
        
        # Varoluş
        existential = specific or morphologically_definite
        
        # Tekil/Çoğul
        singular = 'number=sing' in feats_lower or 'number=' not in feats_lower
        
        return SemanticFeatures(
            specific=specific,
            existential=existential,
            definite=semantically_definite,
            singular=singular,
            morphologically_definite=morphologically_definite,
            semantically_definite=semantically_definite
        )
    
    def calculate_propositional_value(
        self, 
        predicate_type: PredicateType,
        subject_features: SemanticFeatures,
        sentence_type: SentenceType
    ) -> PropositionalValue:
        """
        Önermesel değer hesapla
        
        Analitik önerme: verifiable=1.0, falsifiable=1.0 (mutlak doğru/yanlış)
        Sentetik önerme: verifiable<1.0, falsifiable<1.0 (bağlama bağlı)
        """
        # Soru, istek, hayret → önerme değil
        if sentence_type in [SentenceType.QUESTION, SentenceType.REQUEST, SentenceType.EXCLAMATION]:
            return PropositionalValue(
                proposition_type=PropositionType.NON_PROPOSITIONAL,
                predicate_type=predicate_type,
                sentence_type=sentence_type,
                verifiable=0.0,
                falsifiable=0.0,
                assertive_value=0.0,
                time_bound=False,
                generic=False,
                explanation="Soru/İstek/Hayret tümcelerinin bildirim değeri yok"
            )
        
        # Analitik önerme: Bütüncül yüklem + generic subject
        if predicate_type == PredicateType.HOLISTIC and not subject_features.specific:
            return PropositionalValue(
                proposition_type=PropositionType.ANALYTIC,
                predicate_type=predicate_type,
                sentence_type=SentenceType.PROPERTY,
                verifiable=1.0,
                falsifiable=1.0,
                assertive_value=1.0,
                time_bound=False,
                generic=True,
                explanation="Analitik önerme: Genel-geçer, bütüncül yüklem"
            )
        
        # Sentetik önerme: Parçalı yüklem veya özgül subject
        return PropositionalValue(
            proposition_type=PropositionType.SYNTHETIC,
            predicate_type=predicate_type,
            sentence_type=SentenceType.EVENT if predicate_type == PredicateType.PARTITIVE else SentenceType.HABITUAL,
            verifiable=0.7,   # Bağlama bağlı
            falsifiable=0.7,
            assertive_value=0.8,
            time_bound=predicate_type == PredicateType.PARTITIVE,
            generic=False,
            explanation="Sentetik önerme: Zamana gönderimli, parçalı yüklem"
        )


def analyze_sentence_with_stanza(sentence: str) -> Dict[str, Any]:
    """
    Stanza ile cümle analizi + önermesel semantik
    
    Args:
        sentence: Türkçe cümle
        
    Returns:
        Önermesel analiz sonuçları
    """
    try:
        import stanza
    except ImportError:
        return {
            'error': 'Stanza not installed. Run: pip install stanza',
            'sentence': sentence
        }
    
    # Stanza pipeline (lazy load)
    import os
    global _stanza_nlp
    if _stanza_nlp is None:
        print("Stanza Turkish model yükleniyor...")
        try:
            _stanza_nlp = stanza.Pipeline('tr', verbose=False)
        except:
            print("Model bulunamadı. İndiriliyor: stanza.download('tr')")
            stanza.download('tr')
            _stanza_nlp = stanza.Pipeline('tr', verbose=False)
    
    nlp = _stanza_nlp
    doc = nlp(sentence)
    
    analyzer = TurkishPropositionAnalyzer()
    results = []
    
    # doc may be a Stanza Document with .sentences or already a list of sentences;
    # handle both cases to avoid attribute errors from type checkers.
    if isinstance(doc, list):
        sentences = doc
    else:
        # doc is expected to be a Stanza Document; use getattr to safely obtain .sentences,
        # and fall back to wrapping doc in a list if needed.
        sentences = getattr(doc, 'sentences', [doc])
    
    for sent in sentences:
        # Ana yüklemi bul
        main_verb = None
        subject = None
        
        for word in sent.words:
            if word.deprel == 'root' and word.upos == 'VERB':
                main_verb = word
            if word.deprel == 'nsubj':
                subject = word
        
        if not main_verb:
            continue
        
        # Yüklem tipi analizi
        predicate_type = analyzer.analyze_predicate_type(main_verb.feats or "")
        
        # Özne özellikleri
        subject_features = SemanticFeatures(
            specific=False,
            existential=False,
            definite=False,
            singular=True,
            morphologically_definite=False,
            semantically_definite=False
        )
        
        if subject:
            # Öznenin determiner'ını kontrol et (demonstratives için)
            subject_determiner = None
            for word in sent.words:
                if word.deprel == 'det' and word.head == subject.id:
                    subject_determiner = word
                    break
            
            # Demonstrative varsa özneyi +belirli, +özgül olarak işaretle
            has_demonstrative = (
                subject_determiner and 
                subject_determiner.text.lower() in ['bu', 'şu', 'o']
            )
            
            subject_features = analyzer.analyze_specificity(
                subject.feats or "",
                subject.text,
                subject.upos
            )
            
            # Demonstrative bilgisini ekle
            if has_demonstrative:
                subject_features.specific = True
                subject_features.definite = True
                subject_features.semantically_definite = True
                subject_features.existential = True
        
        # Tümce tipi (basit sınıflandırma)
        sentence_type = SentenceType.PROPERTY if predicate_type == PredicateType.HOLISTIC else SentenceType.EVENT
        
        # Önermesel değer hesapla
        prop_value = analyzer.calculate_propositional_value(
            predicate_type,
            subject_features,
            sentence_type
        )
        
        results.append({
            'sentence': sent.text,
            'main_verb': {
                'text': main_verb.text,
                'lemma': main_verb.lemma,
                'feats': main_verb.feats,
                'predicate_type': predicate_type.value
            },
            'subject': {
                'text': subject.text if subject else None,
                'features': {
                    'specific': subject_features.specific,
                    'existential': subject_features.existential,
                    'definite': subject_features.definite,
                    'singular': subject_features.singular
                }
            } if subject else None,
            'propositional_value': {
                'type': prop_value.proposition_type.value,
                'predicate_type': prop_value.predicate_type.value,
                'sentence_type': prop_value.sentence_type.value,
                'verifiable': prop_value.verifiable,
                'falsifiable': prop_value.falsifiable,
                'assertive_value': prop_value.assertive_value,
                'time_bound': prop_value.time_bound,
                'generic': prop_value.generic,
                'explanation': prop_value.explanation
            }
        })
    
    return {
        'sentence': sentence,
        'analyses': results
    }


def demo_propositional_analysis():
    """Önermesel analiz demo"""
    
    examples = [
        ("Kuşlar uçar", "Analitik önerme - Generic, bütüncül"),
        ("Kuşlar uçtu", "Sentetik önerme - Özgül, parçalı"),
        ("Ali sabahları erken kalkar", "Sentetik - Alışkanlık, özgül+bütüncül"),
        ("Ali dün erken kalktı", "Sentetik - Olay, özgül+parçalı"),
        ("Bir kız tanıdım günde iki paket sigara içer", "Özgül ama belirli değil"),
        ("Bu kız yarın bize gelecek", "Özgül ve belirli"),
        ("Kapıyı açmak istemedim", "Morfolojik belirli, anlamsal belirsiz"),
    ]
    
    print("=" * 70)
    print("TÜRKÇE ÖNERMESEL SEMANTİK ANALİZ")
    print("=" * 70)
    print("\nTeorik Temel:")
    print("  • Analitik Önerme: Bütüncül yüklem + Generic kodlama")
    print("  • Sentetik Önerme: Parçalı yüklem + Özgüllük")
    print("  • Özgüllük ≠ Belirlilik (alıcı perspektifi)")
    print("=" * 70)
    
    for sentence, expected in examples:
        print(f"\n📝 '{sentence}'")
        print(f"   Beklenen: {expected}")
        
        try:
            result = analyze_sentence_with_stanza(sentence)
            
            if 'error' in result:
                print(f"   ⚠️  {result['error']}")
                continue
            
            for analysis in result['analyses']:
                pv = analysis['propositional_value']
                print(f"\n   Analiz:")
                print(f"   • Önerme tipi: {pv['type']}")
                print(f"   • Yüklem tipi: {pv['predicate_type']}")
                print(f"   • Tümce tipi: {pv['sentence_type']}")
                print(f"   • Generic: {pv['generic']}")
                print(f"   • Zamana bağlı: {pv['time_bound']}")
                print(f"   • Doğrulanabilirlik: {pv['verifiable']:.1f}")
                print(f"   • Açıklama: {pv['explanation']}")
                
                if analysis['subject']:
                    subj = analysis['subject']
                    print(f"\n   Özne özellikleri:")
                    print(f"   • Özgül: {subj['features']['specific']}")
                    print(f"   • Belirli: {subj['features']['definite']}")
                    print(f"   • Varoluşsal: {subj['features']['existential']}")
        
        except Exception as e:
            print(f"   ❌ Hata: {e}")


if __name__ == "__main__":
    demo_propositional_analysis()
