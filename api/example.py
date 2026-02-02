"""
API Kullanım Örnekleri
"""

from main import detect_minimalist_errors, detect_centering_errors


def test_minimalist():
    """Minimalist Program ile hata tespiti"""
    print("=== MİNİMALİST PROGRAM ===\n")
    
    # Test 1: Nominal türetme (-DIK) - parser sadece text ve pos verir
    print("Test 1: Nominal türetme (-DIK)")
    words = [
        {"text": "okuduğu", "pos": "VERB"},  # Morfolojiyi API çıkaracak
        {"text": "kitap", "pos": "NOUN"}
    ]
    result = detect_minimalist_errors(words)
    print(f"Toplam hata: {result['total_errors']}")
    for err in result['errors']:
        print(f"  - {err['word']}: {err['reason']}")
    
    # Test 2: Adlaşmış sıfat
    print("\nTest 2: Adlaşmış sıfat")
    words = [
        {"text": "Güzel", "pos": "ADJ"},
        {"text": "adam", "pos": "NOUN"}
    ]
    result = detect_minimalist_errors(words)
    print(f"Toplam hata: {result['total_errors']}")
    for err in result['errors']:
        print(f"  - {err['word']}: {err['reason']}")
    
    # Test 3: -mA eki
    print("\nTest 3: -mA eki")
    words = [
        {"text": "Yazma", "pos": "VERB"},  # Morfolojiyi API çıkaracak
        {"text": "defteri", "pos": "NOUN"}
    ]
    result = detect_minimalist_errors(words)
    print(f"Toplam hata: {result['total_errors']}")
    for err in result['errors']:
        print(f"  - {err['word']}: {err['reason']}")


def test_centering():
    """Merkezleme Kuramı ile söylem analizi"""
    print("\n\n=== MERKEZLEME KURAMI ===\n")
    
    # Test: İyi söylem tutarlılığı
    print("Test: Tutarlı söylem")
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
    
    result = detect_centering_errors(sentences)
    print(f"Söylem skoru: {result['discourse_score']}")
    print(f"Geçişler: {result['transitions']}")
    print(f"Hatalar: {len(result['errors'])}")


def test_combined():
    """Her iki yaklaşımı birlikte kullan"""
    print("\n\n=== KOMBİNE KULLANIM ===\n")
    
    # Parser gerçek çıktısı gibi (morphology yok!)
    test_data = [
        {
            "text": "Ali'nin okuduğu kitap burada.",
            "words": [
                {"text": "Ali'nin", "pos": "PROPN", "dependency": "nmod"},
                {"text": "okuduğu", "pos": "VERB", "dependency": "acl"},  # -DIK API'de çıkarılacak
                {"text": "kitap", "pos": "NOUN", "dependency": "nsubj"},
                {"text": "burada", "pos": "ADV", "dependency": "advmod"}
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
    print("Minimalist Hatalar:")
    for sent in test_data:
        result = detect_minimalist_errors(sent["words"])
        if result['total_errors'] > 0:
            print(f"  {sent['text']}")
            for err in result['errors']:
                print(f"    - {err['word']}: {err['type']} (güven: {err['confidence']})")
    
    # Centering analiz
    print("\nSöylem Tutarlılığı:")
    centering_result = detect_centering_errors(test_data)
    print(f"  Skor: {centering_result['discourse_score']}/4")
    print(f"  Geçişler: {centering_result['transitions']}")


if __name__ == "__main__":
    test_minimalist()
    test_centering()
    test_combined()
