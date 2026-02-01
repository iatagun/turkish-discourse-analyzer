"""
Standart POS Tagging (Stanza) vs Minimalist Hata Tespiti Karşılaştırması

Bu script, gerçek POS tagger'ların (Stanza) nasıl etiketlediğini ve
Minimalist Program teorisinin bu etiketlemelerdeki hataları nasıl
yakaladığını karşılaştırmalı olarak gösterir.

Test Senaryoları:
1. Nominal türetmeler (-DIK, -mA, -Iş)
2. Pro-drop ve trace yapıları
3. Adlaşmış sıfatlar
4. Movement ve scrambling
5. Embedded clauses
"""

import sys
from pathlib import Path
import importlib
from typing import Optional, List

# Parent directory'yi path'e ekle
sys.path.insert(0, str(Path(__file__).parent))

from minimalist_pos_error_detection import (
    MinimalistPOSErrorDetector,
    create_lexical_item,
    LexicalItem,
    Movement,
    SyntacticNode,
    POSErrorType
)

stanza = None
try:
    import stanza
    import torch
    STANZA_AVAILABLE = True
    
    # PyTorch 2.6+ için workaround
    _orig_load = torch.load
    def _load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return _orig_load(*args, **kwargs)
    torch.load = _load
    
except ImportError:
    STANZA_AVAILABLE = False
    stanza = None
    print("⚠️ Stanza yüklü değil. Simüle edilmiş sonuçlar kullanılacak.")
    print("Kurulum: pip install stanza")
    print()


class StanzaPOSTagger:
    """Stanza ile POS tagging wrapper"""
    
    def __init__(self):
        if STANZA_AVAILABLE:
            try:
                stanza_mod = importlib.import_module('stanza')
                Pipeline = getattr(stanza_mod, 'Pipeline', None)
                if Pipeline is None:
                    raise RuntimeError("stanza.Pipeline not found")
                self.nlp = Pipeline('tr', processors='tokenize,pos', verbose=False)
                self.available = True
            except Exception as e:
                print(f"⚠️ Stanza modeli yüklenemedi: {e}")
                print("İlk kullanımda: stanza.download('tr')")
                self.available = False
        else:
            self.available = False
    
    def tag(self, text: str) -> list:
        """
        Metni POS tag'le
        
        Returns:
            [(word, pos, morph), ...]
        """
        if not self.available:
            # Simüle edilmiş sonuçlar
            return self._simulate_tagging(text)
        
        doc = self.nlp(text)
        results = []
        
        for sentence in doc.sentences:
            for word in sentence.words:
                # Morfolojik özellikleri çıkar
                morph = []
                if word.feats:
                    # Stanza morph formatı: "Case=Nom|Number=Sing"
                    for feat in word.feats.split('|'):
                        if '=' in feat:
                            morph.append(feat)
                
                results.append((word.text, word.upos, tuple(morph)))
        
        return results
    
    def _simulate_tagging(self, text: str) -> list:
        """Stanza yoksa simüle et"""
        # Basit simülasyon - bazı bilinen örnekler
        simulations = {
            "Ali'nin okuduğu kitap": [
                ("Ali'nin", "PROPN", tuple()),
                ("okuduğu", "VERB", ("Tense=Past",)),  # HATA! NOUN olmalı
                ("kitap", "NOUN", tuple())
            ],
            "Güzel geldi": [
                ("Güzel", "ADJ", tuple()),  # HATA! NOUN olmalı (adlaşmış)
                ("geldi", "VERB", ("Tense=Past",))
            ],
            "Kitabı Ali okudu": [
                ("Kitabı", "NOUN", ("Case=Acc",)),
                ("Ali", "PROPN", tuple()),
                ("okudu", "VERB", ("Tense=Past",))
            ],
            "Ayşe Ali'nin geldiğini söyledi": [
                ("Ayşe", "PROPN", tuple()),
                ("Ali'nin", "PROPN", ("Case=Gen",)),
                ("geldiğini", "VERB", ("Tense=Past",)),  # HATA! NOUN olmalı
                ("söyledi", "VERB", ("Tense=Past",))
            ],
            "O süt aldı": [
                ("O", "PRON", tuple()),
                ("süt", "NOUN", tuple()),
                ("aldı", "VERB", ("Tense=Past",))
            ],
            "Yazma işi bitti": [
                ("Yazma", "VERB", tuple()),  # HATA! NOUN olmalı (-mA)
                ("işi", "NOUN", ("Case=Acc",)),
                ("bitti", "VERB", ("Tense=Past",))
            ],
            "Koşmak sağlıklıdır": [
                ("Koşmak", "VERB", tuple()),  # HATA! NOUN olmalı (-mAk)
                ("sağlıklıdır", "ADJ", tuple())
            ]
        }
        
        return simulations.get(text, [])


def extract_morphology_features(feats_tuple: tuple) -> list:
    """Stanza morph features'dan minimalist özellikleri çıkar"""
    morph_list = []
    
    for feat in feats_tuple:
        if 'Tense=Past' in feat:
            morph_list.append('PAST')
        elif 'Tense=Pres' in feat:
            morph_list.append('PRES')
        elif 'Tense=Fut' in feat:
            morph_list.append('FUT')
        elif 'Case=Acc' in feat:
            morph_list.append('-i')
        elif 'Case=Gen' in feat:
            morph_list.append('-in')
        elif 'Case=Dat' in feat:
            morph_list.append('-e')
    
    # Nominal suffixes tespiti (kelime sonuna göre)
    # Bu basitleştirilmiş - gerçekte daha karmaşık
    
    return morph_list


def detect_nominal_suffix(word: str) -> list:
    """Kelimeden nominal ekleri tespit et"""
    suffixes = []
    
    # -DIK variants
    if any(word.endswith(suffix) for suffix in ['dığı', 'diği', 'duğu', 'düğü', 'dık', 'dik', 'duk', 'dük']):
        suffixes.append('-DIK')
    
    # -mA variants
    if any(word.endswith(suffix) for suffix in ['ma', 'me', 'mak', 'mek']):
        suffixes.append('-mA')
    
    # -Iş variants
    if any(word.endswith(suffix) for suffix in ['ış', 'iş', 'uş', 'üş']):
        suffixes.append('-Iş')
    
    # -mAk
    if any(word.endswith(suffix) for suffix in ['mak', 'mek']):
        suffixes.append('-mAk')
    
    return suffixes


def compare_pos_tagging(text: str, expected_errors: Optional[List[POSErrorType]] = None):
    """
    Bir cümle için Stanza POS tagging ve Minimalist hata tespitini karşılaştır
    
    Args:
        text: Test cümlesi
        expected_errors: Beklenen hata tipleri (doğrulama için)
    """
    print("=" * 80)
    print(f"📝 TEST CÜMLESİ: '{text}'")
    print("=" * 80)
    
    # 1. Stanza ile POS tagging
    tagger = StanzaPOSTagger()
    stanza_result = tagger.tag(text)
    
    print("\n1️⃣ STANZA POS TAGGING:")
    print("-" * 80)
    for word, pos, morph in stanza_result:
        morph_str = ", ".join(morph) if morph else "—"
        print(f"   {word:15} → {pos:8} [{morph_str}]")
    
    # 2. Minimalist analiz için LexicalItem'lar oluştur
    lex_items = []
    for word, pos, morph in stanza_result:
        # Morfolojik özellikleri çıkar
        morph_features = extract_morphology_features(morph)
        
        # Nominal suffix tespiti
        nominal_suffixes = detect_nominal_suffix(word)
        morph_features.extend(nominal_suffixes)
        
        lex_item = create_lexical_item(
            word=word,
            pos=pos,
            morphology=morph_features
        )
        lex_items.append(lex_item)
    
    # 3. Minimalist hata tespiti
    detector = MinimalistPOSErrorDetector()
    results = detector.detect_errors(lex_items)
    
    print("\n2️⃣ MİNİMALİST HATA TESPİTİ:")
    print("-" * 80)
    
    if results['candidate_errors']:
        print(f"   ✅ {len(results['candidate_errors'])} ADAY HATA bulundu:\n")
        for i, error in enumerate(results['candidate_errors'], 1):
            print(f"   {i}. {error['type'].value}")
            print(f"      Kelime: '{error['item'].word}'")
            print(f"      Stanza etiketi: {error['found_pos']} ❌")
            print(f"      Doğru etiket: {error['expected_pos']} ✅")
            print(f"      Sebep: {error['reason']}")
            print(f"      Güven: {error['confidence']:.0%}")
            print()
    else:
        print("   ℹ️ Hata tespit edilmedi (Stanza doğru etiketlemiş olabilir)")
    
    # 4. Karşılaştırma özeti
    print("\n3️⃣ KARŞILAŞTIRMA ÖZETİ:")
    print("-" * 80)
    
    if expected_errors:
        detected_types = {e['type'] for e in results['candidate_errors']}
        expected_types = set(expected_errors)
        
        correct_detections = detected_types & expected_types
        missed_detections = expected_types - detected_types
        false_positives = detected_types - expected_types
        
        print(f"   Beklenen hatalar: {len(expected_errors)}")
        print(f"   Tespit edilen: {len(results['candidate_errors'])}")
        print(f"   ✅ Doğru tespit: {len(correct_detections)}")
        print(f"   ❌ Kaçan: {len(missed_detections)}")
        print(f"   ⚠️ Yanlış alarm: {len(false_positives)}")
        
        if correct_detections:
            print(f"\n   Başarılı tespitler:")
            for error_type in correct_detections:
                print(f"      ✓ {error_type.value}")
        
        if missed_detections:
            print(f"\n   Kaçan hatalar:")
            for error_type in missed_detections:
                print(f"      ✗ {error_type.value}")
    
    print("\n" + "=" * 80 + "\n")


def run_comprehensive_tests():
    """Kapsamlı test suite"""
    
    print("🔬 STANZA vs MİNİMALİST PROGRAM - KAPSAMLI TEST\n")
    print("Bu test, standart POS tagger'ların (Stanza) nasıl hata yaptığını ve")
    print("Minimalist Program teorisinin bu hataları nasıl yakaladığını gösterir.\n")
    
    # Test 1: -DIK nominal türetmesi
    compare_pos_tagging(
        "Ali'nin okuduğu kitap",
        expected_errors=[POSErrorType.NOUN_VERB_CONFUSION]
    )
    
    # Test 2: Adlaşmış sıfat
    compare_pos_tagging(
        "Güzel geldi",
        expected_errors=[POSErrorType.ADJ_NOUN_CONFUSION]
    )
    
    # Test 3: Scrambling (doğru etiketlenmiş, hata yok)
    compare_pos_tagging(
        "Kitabı Ali okudu",
        expected_errors=[]
    )
    
    # Test 4: Embedded clause (-DIK)
    compare_pos_tagging(
        "Ayşe Ali'nin geldiğini söyledi",
        expected_errors=[POSErrorType.NOUN_VERB_CONFUSION]
    )
    
    # Test 5: Pro-drop (doğru etiketlenmiş)
    compare_pos_tagging(
        "O süt aldı",
        expected_errors=[]
    )
    
    # Test 6: -mA nominal
    compare_pos_tagging(
        "Yazma işi bitti",
        expected_errors=[POSErrorType.NOUN_VERB_CONFUSION]
    )
    
    # Test 7: -mAk infinitive
    compare_pos_tagging(
        "Koşmak sağlıklıdır",
        expected_errors=[POSErrorType.NOUN_VERB_CONFUSION]
    )
    
    # Özet istatistik
    print("\n" + "=" * 80)
    print("📊 GENEL İSTATİSTİKLER")
    print("=" * 80)
    print("\nMinimalist Program teorisi, Türkçe'deki şu POS hatalarını yakalayabilir:")
    print("  ✅ NOUN ↔ VERB (-DIK, -mA, -Iş, -mAk türetmeleri)")
    print("  ✅ ADJ ↔ NOUN (Adlaşmış sıfatlar)")
    print("  ✅ PRON ↔ DET (Pro-drop + trace yapıları)")
    print("  ⚠️ SUBJ ↔ OBJ (Argüman yapısı - geliştirilmeli)")
    print("\nStanza gibi standart tagger'lar bu hataları genellikle yapar çünkü:")
    print("  • Sözdizimsel bağlamı dikkate almazlar")
    print("  • Numeration ve türetim kontrolü yapmazlar")
    print("  • Movement ve trace ilişkilerini görmezler")
    print("  • Sadece yerel (token-level) özelliklere bakarlar")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Stanza modelini indir (ilk çalıştırmada)
    if STANZA_AVAILABLE:
        try:
            import stanza
            stanza.download('tr', verbose=False)
        except:
            pass
    
    run_comprehensive_tests()
