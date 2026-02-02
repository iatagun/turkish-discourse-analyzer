"""
Test: Propositional Semantics + POS Tagging Integration
=========================================================

Bu test, önermesel semantik analizin POS tagging tercihlerini 
nasıl güçlendirdiğini gösterir.
"""

import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from api.enhanced_analysis import check_sentence_enhanced

test_cases = [
    {
        'sentence': "Ali'nin okuduğu kitap burada.",
        'expected': {
            'pos_preference': 'okuduğu → NOUN (nominal domain)',
            'semantic_support': '-DIK eki → parçalı yüklem → özgüllük → nominal',
            'confidence_boost': '0.90 → 0.95'
        }
    },
    {
        'sentence': "Yazma defteri aldım.",
        'expected': {
            'pos_preference': 'Yazma → NOUN (productive -mA)',
            'semantic_support': 'Productive -mA (not lexicalized)',
            'confidence': '0.80-0.85'
        }
    },
    {
        'sentence': "Yüzme havuzu temiz.",
        'expected': {
            'pos_preference': 'None (lexicalized compound)',
            'semantic_support': 'yüzme → lexicalized (no preference)',
            'confidence': 'N/A'
        }
    },
    {
        'sentence': "Kuşlar uçar.",
        'expected': {
            'pos_preference': 'None expected',
            'semantic_support': 'Analytic proposition (generic + holistic)',
            'confidence': 'N/A'
        }
    }
]

print("=" * 80)
print("PROPOSITIONAL SEMANTICS + POS TAGGING INTEGRATION TEST")
print("=" * 80)

for i, test in enumerate(test_cases, 1):
    sentence = test['sentence']
    expected = test['expected']
    
    print(f"\n{'='*80}")
    print(f"TEST {i}: {sentence}")
    print(f"{'='*80}")
    
    result = check_sentence_enhanced(sentence)
    
    # POS Analysis
    pos = result.get('pos_analysis', {})
    errors = pos.get('errors', [])
    
    print(f"\n📊 POS PREFERENCES:")
    if errors:
        for err in errors:
            confidence = err.get('confidence', 0)
            semantic_marker = "[SEMANTIC]" if "Semantically verified" in err.get('reason', '') else ""
            print(f"  • {err['word']}: {err['type']}")
            print(f"    Confidence: {confidence:.0%} {semantic_marker}")
            if err.get('reason'):
                print(f"    Reason: {err['reason']}")
    else:
        print(f"  ✓ No preferences detected")
    
    # Propositional Analysis
    prop = result.get('propositional', {})
    if 'analyses' in prop and prop['analyses']:
        analysis = prop['analyses'][0]
        pv = analysis['propositional_value']
        
        print(f"\n🔬 SEMANTIC ANALYSIS:")
        print(f"  • Proposition: {pv['type']}")
        print(f"  • Predicate: {pv['predicate_type']}")
        print(f"  • Generic: {pv['generic']}")
        print(f"  • Time-bound: {pv['time_bound']}")
        
        subject = analysis.get('subject_features', {})
        if subject:
            print(f"\n  Subject Features:")
            print(f"    - Specific: {subject.get('specific', False)}")
            print(f"    - Definite: {subject.get('definite', False)}")
            print(f"    - Existential: {subject.get('existential', False)}")
    
    # Theoretical Connection
    if 'theoretical_explanation' in result:
        print(f"\n💡 THEORETICAL CONNECTION:")
        print(result['theoretical_explanation'])
    
    print(f"\n✅ EXPECTED:")
    for key, value in expected.items():
        print(f"  • {key}: {value}")

print(f"\n{'='*80}")
print("TEST COMPLETED")
print("=" * 80)
