import os
os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD'] = '0'

from api.pos_semantic_analyzer import analyze_text
import json

# Test cümleleri
test_sentences = [
    "Ali'nin okuduğu kitap burada.",
    "Kuşlar uçar.",
    "Yüzme havuzu temiz.",
    "Yazma defteri aldım."
]

print("="*80)
print("STANZA EKSIK ETİKETLEME TESPİTİ - PREFERENCES SUMMARY")
print("="*80)

for text in test_sentences:
    result = analyze_text(text)
    
    print(f"\n📝 {text}")
    print("-"*80)
    
    preferences = result["sentences"][0]["preferences"]
    
    if preferences:
        print("✅ Stanza'nın eksik etiketledikleri:")
        for pref in preferences:
            print(f"\n  Kelime: {pref['word']}")
            print(f"  Stanza POS: {pref['stanza_pos']}")
            print(f"  Önerilen POS: {pref['suggested_pos']}")
            print(f"  Güven: {pref['confidence']:.0%}")
            print(f"  Sebep: {pref['reason']}")
    else:
        print("✅ Preference yok (Stanza doğru etiketlemiş)")

print("\n" + "="*80)
print("JSON FORMAT ÖRNEK")
print("="*80)

result = analyze_text("Ali'nin okuduğu kitap burada.")
print(json.dumps(result["sentences"][0]["preferences"], indent=2, ensure_ascii=False))
