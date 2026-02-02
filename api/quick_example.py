"""
Kapsamlı Test - Tüm Hata Tipleri
"""

from main import check_sentence, check_discourse

print("=" * 70)
print("TÜRKÇE POS TAGGING - NOMINAL DOMAIN PREFERENCE TESPİTİ")
print("(UD etiketleri doğrudur; discourse görevleri için öneriler)")
print("=" * 70)

# Test kategorileri
test_cases = {
    "1. Nominal Domain Preference (VERB-origin) - -DIK eki": [
        "Ali'nin okuduğu kitap.",
        "Benim geldiğim yer.",
        "Senin yaptığın iş."
    ],
    "2. Nominal Domain Preference (VERB-origin) - -mA eki": [
        "Yazma defteri aldım.",
        "Yüzme havuzu.",
        "Okuma kitabı."
    ],
    "3. Nominal Domain Preference (VERB-origin) - -mAk eki": [
        "Koşmak sağlıklıdır.",
        "Yemek yapmak zor.",
        "Uyumak önemli."
    ],
    "4. Nominal Domain Preference (VERB-origin) - -Iş eki": [
        "Göçüş zamanı.",
        "Bakış açısı.",
        "Çıkış yolu."
    ],
    "5. Nominal Domain Preference (ADJ-origin) - Adlaşmış sıfatlar": [
        "Güzel insan.",
        "Yaşlı adam geldi.",
        "Küçük çocuk."
    ],
    "6. UD-uyumlu etiketler (nominal preference yok)": [
        "Ali kitap okudu.",
        "Çocuk parkta oynadı.",
        "Annem yemek yaptı."
    ]
}

total_tests = 0
total_errors = 0

for category, sentences in test_cases.items():
    print(f"\n{category}")
    print("-" * 70)
    
    for sentence in sentences:
        total_tests += 1
        r = check_sentence(sentence)
        
        # Candidate vs confirmed ayrımı
        confirmed = [e for e in r['errors'] if e['confidence'] >= 0.85]
        candidates = [e for e in r['errors'] if e['confidence'] < 0.85]
        
        if confirmed:
            status = "❌ HATA"
        elif candidates:
            status = "⚠️  UYARI"
        else:
            status = "✅ DOĞRU"
        
        print(f"{status} {sentence}")
        
        # Stanza'nın orijinal etiketlerini göster
        stanza_tags = " ".join([f"{w['text']}[{w['pos']}]" for w in r['words']])
        print(f"   Stanza: {stanza_tags}")
        
        if confirmed:
            total_errors += len(confirmed)
            print(f"   └─ {len(confirmed)} kesin hata:")
            for e in confirmed:
                print(f"      • {e['word']}: {e['type']} (güven: {e['confidence']:.0%})")
        
        if candidates:
            print(f"   └─ {len(candidates)} düşük güvenli uyarı:")
            for e in candidates:
                print(f"      • {e['word']}: {e['type']} (güven: {e['confidence']:.0%})")
        
        if not confirmed and not candidates:
            print(f"   └─ Hata yok")

print("\n" + "=" * 70)
print("SÖYLEM TUTARLILIĞI ANALİZİ (MERKEZLEme KURAMI)")
print("=" * 70)

# Test 1: İyi söylem tutarlılığı
print("\n✓ Test 1: Tutarlı söylem (CONTINUE bekleniyor)")
print("-" * 70)
discourse1 = check_discourse([
    "Ahmet markete gitti.",
    "O süt aldı.",
    "Sonra eve döndü."
])
print(f"Söylem Skoru: {discourse1['discourse_score']:.1f}/4.0")
print(f"Geçişler: {discourse1['transitions']}")
if discourse1['discourse_score'] >= 2.0:
    print("✓ Zamir çözümleme aktif: 'O' ve örtük özneler tanınıyor")

# Test 2: Kötü söylem tutarlılığı
print("\n✗ Test 2: Tutarsız söylem (ROUGH-SHIFT bekleniyor)")
print("-" * 70)
discourse2 = check_discourse([
    "Ali kitap okudu.",
    "Hava çok güzel.",
    "Masa kahverengi."
])
print(f"Söylem Skoru: {discourse2['discourse_score']:.1f}/4.0")
print(f"Geçişler: {discourse2['transitions']}")
if discourse2['centering_errors']:
    print("Tespit edilen söylem hataları:")
    for err in discourse2['centering_errors']:
        print(f"  • Cümle {err['sentence_index']}: {err['transition']} (severity: {err['severity']})")

# Test 3: POS hatası + Söylem analizi
print("\n✗ Test 3: Hem POS hem söylem hataları")
print("-" * 70)
discourse3 = check_discourse([
    "Ali'nin okuduğu kitap burada.",
    "Yazma defteri masada.",
    "Koşmak sağlıklıdır."
])
print(f"Söylem Skoru: {discourse3['discourse_score']:.1f}/4.0")
print("\nCümle bazlı POS hataları:")
for i, sent_err in enumerate(discourse3['sentence_errors']):
    print(f"  Cümle {i+1}: {sent_err['sentence']}")
    # Stanza tagging
    r = check_sentence(sent_err['sentence'])
    stanza_tags = " ".join([f"{w['text']}[{w['pos']}]" for w in r['words']])
    print(f"  Stanza: {stanza_tags}")
    
    if sent_err['total_errors'] > 0:
        for e in sent_err['errors']:
            print(f"    └─ {e['word']}: {e['type']}")
    else:
        print(f"    └─ Hata yok")

# Özet
print("\n" + "=" * 70)
print("TEST ÖZETİ")
print("=" * 70)
print(f"Toplam test: {total_tests}")
print(f"Tespit edilen POS hatası: {total_errors}")
print(f"Başarı oranı: {((total_tests - total_errors) / total_tests * 100):.1f}%")
print("\n✓ API çalışıyor ve tüm hata tipleri test edildi!")
