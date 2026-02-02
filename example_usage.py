"""
Structured Output API Kullanım Örneği
======================================

Bu dosya structured_output.py API'sinin nasıl kullanılacağını gösterir.
"""

import json
from api.structured_output import analyze_text, analyze_to_conllu

def example_json_output():
    """JSON formatında tam Stanza çıktısı + extensions"""
    print("=" * 80)
    print("ÖRNEK 1: JSON FORMAT (Stanza + POS Preferences + Semantics)")
    print("=" * 80)
    
    text = "Ali'nin okuduğu kitap burada."
    result = analyze_text(text)
    
    print(f"\n📝 Cümle: {text}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def example_word_level():
    """Kelime düzeyinde bilgilere erişim"""
    print("\n" + "=" * 80)
    print("ÖRNEK 2: Kelime Düzeyinde Analiz")
    print("=" * 80)
    
    text = "Kuşlar uçtu."
    result = analyze_text(text)
    
    print(f"\n📝 Cümle: {text}\n")
    
    for word in result["sentences"][0]["words"]:
        if word["upos"] == "PUNCT":
            continue
        
        print(f"Kelime: {word['text']}")
        print(f"  • Lemma: {word['lemma']}")
        print(f"  • POS: {word['upos']}")
        print(f"  • Dependency: {word['deprel']}")
        print(f"  • Morphology: {word['morphology']}")
        print(f"  • Is Finite: {word['is_finite']}")
        
        if word['preference']:
            pref = word['preference']
            print(f"  • POS Preference: {pref['expected_pos']} (confidence: {pref['confidence']:.0%})")
            print(f"    Reason: {pref['reason']}")
        
        print()


def example_sentence_semantics():
    """Cümle düzeyinde semantik analiz"""
    print("=" * 80)
    print("ÖRNEK 3: Cümle Düzeyinde Semantik Analiz")
    print("=" * 80)
    
    examples = [
        "Kuşlar uçar.",           # Analytic, generic
        "Kuşlar uçtu.",           # Synthetic, past event
        "Ali sabahları erken kalkar.",  # Synthetic, habitual
        "Yüzme havuzu temiz."     # Synthetic, copula
    ]
    
    for text in examples:
        result = analyze_text(text)
        semantics = result["sentences"][0]["semantics"]
        
        print(f"\n📝 {text}")
        print(f"  Proposition Type: {semantics['proposition_type']}")
        print(f"  Predicate Type: {semantics['predicate_type']}")
        print(f"  Clause Finiteness: {semantics['clause_finiteness']}")
        print(f"  Generic: {semantics['generic_encoding']}")
        print(f"  Time-bound: {semantics['time_bound']}")
        print(f"  Verifiability: {semantics['verifiability']}")


def example_conllu():
    """CONLL-U formatında çıktı"""
    print("\n" + "=" * 80)
    print("ÖRNEK 4: CONLL-U Format")
    print("=" * 80)
    
    text = "Ali'nin okuduğu kitap burada."
    conllu = analyze_to_conllu(text)
    
    print(f"\n{conllu}")


def example_pos_preferences():
    """Sadece POS preferences çıkar"""
    print("=" * 80)
    print("ÖRNEK 5: POS Preferences Listesi")
    print("=" * 80)
    
    texts = [
        "Ali'nin okuduğu kitap burada.",
        "Yazma defteri aldım.",
        "Yüzme havuzu temiz."  # Lexicalized - preference yok
    ]
    
    for text in texts:
        result = analyze_text(text, include_semantics=False)
        
        preferences = [
            w for w in result["sentences"][0]["words"] 
            if w.get("preference")
        ]
        
        print(f"\n📝 {text}")
        if preferences:
            for w in preferences:
                pref = w["preference"]
                print(f"  ✓ {w['text']}: {w['upos']} → {pref['expected_pos']}")
                print(f"    Confidence: {pref['confidence']:.0%}")
                print(f"    Reason: {pref['reason']}")
        else:
            print("  ✓ No POS preferences detected (UD-compliant or lexicalized)")


if __name__ == "__main__":
    # Tüm örnekleri çalıştır
    example_json_output()
    example_word_level()
    example_sentence_semantics()
    example_conllu()
    example_pos_preferences()
    
    print("\n" + "=" * 80)
    print("API kullanım örnekleri tamamlandı!")
    print("=" * 80)
