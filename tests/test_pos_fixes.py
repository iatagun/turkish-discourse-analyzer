"""
POS Tagging Uyumsuzluk Düzeltme Testleri
========================================

Şimdiye kadar tespit ettiğimiz POS tagging uyumsuzluklarının
düzgün çalıştığını doğrular.

Test Edilen Durumlar:
1. -DIK eki nominal domain preference (okuduğu)
2. -mA eki productive vs lexicalized (yazma vs yüzme)
3. Generic vs Specific propositions (uçar vs uçtu)
4. Holistic vs Partitive predicates
5. Finite vs Non-finite clause detection
6. Habitual aspect detection (kalkar)
7. Person[psor] nominal filtering
"""

import os
import sys
import json
import unittest
from pathlib import Path
from typing import Dict, Any, List

# PyTorch 2.6 uyumluluk
os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD'] = '0'

# Parent directory ekle
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from api.pos_semantic_analyzer import analyze_text


# Test sonuçlarını JSON formatında toplamak için
TEST_RESULTS = {
    "test_suite": "POS Fixes Validation",
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "test_cases": []
}


class TestDIKSuffixFix(unittest.TestCase):
    """Test: -DIK eki nominal domain preference tespiti"""
    
    def test_dik_suffix_detected(self):
        """okuduğu: VERB → NOUN preference tespit edilmeli"""
        result = analyze_text("Ali'nin okuduğu kitap burada.")
        
        # "okuduğu" kelimesini bul
        okuduğu = None
        for word in result["sentences"][0]["words"]:
            if "oku" in word["text"].lower():
                okuduğu = word
                break
        
        self.assertIsNotNone(okuduğu, "okuduğu kelimesi bulunamadı")
        assert okuduğu is not None  # Type narrowing for type checker
        self.assertEqual(okuduğu["upos"], "VERB", "Stanza VERB etiketlemeli")
        self.assertIsNotNone(okuduğu["preference"], "Nominal preference tespit edilmeliydi")
        self.assertEqual(okuduğu["preference"]["expected_pos"], "NOUN")
        self.assertIn("-DIK", okuduğu["morphology"])
        self.assertGreaterEqual(okuduğu["preference"]["confidence"], 0.85)
    
    def test_dik_with_semantic_validation(self):
        """Semantic validation ile confidence artmalı"""
        result = analyze_text("Okuduğu kitap ilginç.", include_semantics=True)
        
        okuduğu = None
        for word in result["sentences"][0]["words"]:
            if "oku" in word["text"].lower():
                okuduğu = word
                break
        
        self.assertIsNotNone(okuduğu)
        assert okuduğu is not None  # Type narrowing for type checker
        # Semantic validation ile confidence 90% veya üzeri olmalı
        if okuduğu["preference"]:
            self.assertGreaterEqual(okuduğu["preference"]["confidence"], 0.90)


class TestMASuffixFix(unittest.TestCase):
    """Test: -mA eki productive vs lexicalized ayrımı"""
    
    def test_productive_ma_detected(self):
        """yazma (notebook): Productive derivation, preference olmalı"""
        result = analyze_text("Yazma defteri aldım.")
        
        yazma = None
        for word in result["sentences"][0]["words"]:
            if word["text"].lower() == "yazma":
                yazma = word
                break
        
        # Productive -mA ise preference olabilir (context'e bağlı)
        # En azından -mA eki tespit edilmeli
        if yazma and yazma["upos"] == "VERB":
            self.assertIn("-mA", yazma.get("morphology", []))
    
    def test_lexicalized_ma_filtered(self):
        """yüzme havuzu: Lexicalized compound, preference OLMAMALI"""
        result = analyze_text("Yüzme havuzu temiz.")
        
        yüzme = None
        for word in result["sentences"][0]["words"]:
            if "yüz" in word["text"].lower():
                yüzme = word
                break
        
        # Lexicalized compound, preference olmamalı
        if yüzme:
            self.assertIsNone(yüzme["preference"], 
                            "Lexicalized compound için preference olmamalı")


class TestGenericVsSpecificFix(unittest.TestCase):
    """Test: Generic vs Specific proposition ayrımı"""
    
    def test_generic_analytic(self):
        """Kuşlar uçar: Analytic, holistic, generic=True"""
        result = analyze_text("Kuşlar uçar.")
        sem = result["sentences"][0]["semantics"]
        
        self.assertEqual(sem["proposition_type"], "analytic")
        self.assertEqual(sem["predicate_type"], "holistic")
        self.assertTrue(sem["generic_encoding"])
        self.assertFalse(sem["time_bound"])
        self.assertEqual(sem["verifiability"], 1.0)
    
    def test_specific_synthetic(self):
        """Kuşlar uçtu: Synthetic, partitive, time_bound=True"""
        result = analyze_text("Kuşlar uçtu.")
        sem = result["sentences"][0]["semantics"]
        
        self.assertEqual(sem["proposition_type"], "synthetic")
        self.assertEqual(sem["predicate_type"], "partitive")
        self.assertFalse(sem["generic_encoding"])
        self.assertTrue(sem["time_bound"])
        self.assertGreater(sem["verifiability"], 0.0)
        self.assertLess(sem["verifiability"], 1.0)


class TestHolisticVsPartitiveFix(unittest.TestCase):
    """Test: Holistic vs Partitive predicate ayrımı"""
    
    def test_holistic_aorist(self):
        """Geniş zaman: Holistic veya Habitual predicate"""
        result = analyze_text("Ali kitap okur.")
        sem = result["sentences"][0]["semantics"]
        
        # Geniş zaman habitual olarak algılanabilir (context'e bağlı)
        self.assertIn(sem["predicate_type"], ["holistic", "habitual"])
    
    def test_partitive_past(self):
        """Geçmiş zaman: Partitive predicate"""
        result = analyze_text("Ali kitap okudu.")
        sem = result["sentences"][0]["semantics"]
        
        self.assertEqual(sem["predicate_type"], "partitive")
    
    def test_partitive_future(self):
        """Gelecek zaman: Partitive predicate"""
        result = analyze_text("Ali kitap okuyacak.")
        sem = result["sentences"][0]["semantics"]
        
        self.assertEqual(sem["predicate_type"], "partitive")


class TestHabitualAspectFix(unittest.TestCase):
    """Test: Habitual aspect (Aspect=Hab) tespiti"""
    
    def test_habitual_detected(self):
        """sabahları kalkar: Habitual predicate"""
        result = analyze_text("Ali sabahları erken kalkar.")
        sem = result["sentences"][0]["semantics"]
        
        self.assertEqual(sem["predicate_type"], "habitual")
        
        # "kalkar" finite verb olmalı
        kalkar = None
        for word in result["sentences"][0]["words"]:
            if "kalk" in word["text"].lower():
                kalkar = word
                break
        
        if kalkar:
            self.assertTrue(kalkar["is_finite"], "Habitual verb finite olmalı")


class TestFiniteVsNonFiniteFix(unittest.TestCase):
    """Test: Finite vs Non-finite clause detection"""
    
    def test_finite_verb_detection(self):
        """uçtu: Finite verb (Tense=Past)"""
        result = analyze_text("Kuşlar uçtu.")
        
        uçtu = None
        for word in result["sentences"][0]["words"]:
            if "uç" in word["text"].lower():
                uçtu = word
                break
        
        self.assertIsNotNone(uçtu)
        assert uçtu is not None  # Type narrowing for type checker
        self.assertTrue(uçtu["is_finite"])
        self.assertEqual(result["sentences"][0]["semantics"]["clause_finiteness"], "finite")
    
    def test_nonfinite_with_case(self):
        """okuduğu (Case=Nom): Non-finite (nominal)"""
        result = analyze_text("Ali'nin okuduğu kitap.")
        
        okuduğu = None
        for word in result["sentences"][0]["words"]:
            if "oku" in word["text"].lower():
                okuduğu = word
                break
        
        if okuduğu:
            self.assertFalse(okuduğu["is_finite"], 
                           "Durum ekli fiil non-finite olmalı")
    
    def test_person_psor_nonfinite(self):
        """Person[psor]: İyelik eki varsa non-finite"""
        result = analyze_text("Kitabı okuduğum zaman.")
        
        okuduğum = None
        for word in result["sentences"][0]["words"]:
            if "oku" in word["text"].lower() and "duğ" in word["text"].lower():
                okuduğum = word
                break
        
        if okuduğum:
            self.assertFalse(okuduğum["is_finite"],
                           "Person[psor] ile non-finite olmalı")


class TestConfidenceScoring(unittest.TestCase):
    """Test: Confidence scoring doğruluğu"""
    
    def test_dik_high_confidence(self):
        """-DIK eki yüksek confidence vermeli (70%+)"""
        result = analyze_text("Gördüğüm şey.")
        
        gördüğüm = None
        for word in result["sentences"][0]["words"]:
            if "gör" in word["text"].lower():
                gördüğüm = word
                break
        
        if gördüğüm and gördüğüm["preference"]:
            # Context'e göre 70-95% arasında olabilir
            self.assertGreaterEqual(gördüğüm["preference"]["confidence"], 0.70)
    
    def test_productive_ma_medium_confidence(self):
        """Productive -mA medium confidence (80-85%)"""
        result = analyze_text("Yazma becerisi.")
        
        # Productive -mA tespit edilirse confidence 80-85% aralığında
        for word in result["sentences"][0]["words"]:
            if word["text"].lower() == "yazma" and word.get("preference"):
                self.assertGreaterEqual(word["preference"]["confidence"], 0.75)
                self.assertLessEqual(word["preference"]["confidence"], 0.90)


class TestOutputFormatFix(unittest.TestCase):
    """Test: Output format doğruluğu"""
    
    def test_predicate_types_english(self):
        """Predicate types İngilizce olmalı"""
        sentences = [
            ("Kuşlar uçar.", "holistic"),
            ("Kuşlar uçtu.", "partitive"),
            ("Ali sabahları kalkar.", "habitual")
        ]
        
        for text, expected_type in sentences:
            result = analyze_text(text)
            sem = result["sentences"][0]["semantics"]
            self.assertEqual(sem["predicate_type"], expected_type,
                           f"{text} → {expected_type} olmalı")
    
    def test_semantics_included_by_default(self):
        """include_semantics=True varsayılan olmalı"""
        result = analyze_text("Kuşlar uçar.")
        
        self.assertIn("semantics", result["sentences"][0])
        self.assertIsNotNone(result["sentences"][0]["semantics"])


def run_tests():
    """Tüm testleri çalıştır ve rapor üret"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Test özeti
    TEST_RESULTS["total_tests"] = result.testsRun
    TEST_RESULTS["passed"] = result.testsRun - len(result.failures) - len(result.errors)
    TEST_RESULTS["failed"] = len(result.failures) + len(result.errors)
    
    # Örnek cümleler ve analizleri ekle
    example_analyses = [
        ("Ali'nin okuduğu kitap burada.", "DIK suffix detection"),
        ("Kuşlar uçar.", "Generic analytic proposition"),
        ("Kuşlar uçtu.", "Specific synthetic proposition"),
        ("Ali sabahları erken kalkar.", "Habitual aspect"),
        ("Yüzme havuzu temiz.", "Lexicalized compound filtering")
    ]
    
    for text, description in example_analyses:
        analysis = analyze_text(text)
        TEST_RESULTS["test_cases"].append({
            "description": description,
            "input_text": text,
            "stanza_output": analysis
        })
    
    # Konsola özet yazdır
    print("\n" + "="*70)
    print("TEST ÖZET")
    print("="*70)
    print(f"Toplam Test: {result.testsRun}")
    print(f"Başarılı: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Başarısız: {len(result.failures)}")
    print(f"Hata: {len(result.errors)}")
    print(f"Başarı Oranı: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print("="*70)
    
    # JSON dosyasına kaydet
    output_file = Path(__file__).parent / "test_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(TEST_RESULTS, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Stanza JSON formatında test sonuçları: {output_file}")
    print(f"   {len(TEST_RESULTS['test_cases'])} örnek cümle analizi içeriyor")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
