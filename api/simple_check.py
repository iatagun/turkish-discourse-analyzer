"""
Simple API: POS Preference Detection with Optional Semantic Enhancement

Kullanım:
    from api.simple_check import check_sentence
    
    # Basit kullanım
    result = check_sentence("Ali'nin okuduğu kitap burada.")
    
    # Semantic enhancement ile
    result = check_sentence("Kuşlar uçar.", include_semantics=True)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import stanza
from typing import Dict, List, Any

# Stanza pipeline (lazy load)
_nlp: Any = None

def get_nlp() -> Any:
    global _nlp
    if _nlp is None:
        print("Loading Stanza Turkish model...")
        _nlp = stanza.Pipeline('tr', processors='tokenize,mwt,pos,lemma,depparse', verbose=False)
    return _nlp


# Propositional semantics (optional)
try:
    # Add src directory to path
    _src_path = Path(__file__).parent.parent / 'src'
    if str(_src_path) not in sys.path:
        sys.path.insert(0, str(_src_path))
    
    from propositional_semantics import (  # type: ignore
        TurkishPropositionAnalyzer,
        analyze_sentence_with_stanza,
        PredicateType
    )
    PROPOSITIONAL_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PROPOSITIONAL_AVAILABLE = False
    TurkishPropositionAnalyzer = None  # type: ignore
    PredicateType = None  # type: ignore
    analyze_sentence_with_stanza = None  # type: ignore


def check_sentence(sentence: str, include_semantics: bool = False) -> Dict:
    """
    POS tagging preferences tespit et, opsiyonel olarak semantic analiz ekle
    
    Args:
        sentence: Türkçe cümle
        include_semantics: Önermesel semantik analiz ekle (default: False)
        
    Returns:
        {
            'sentence': str,
            'preferences': [...],
            'summary': {...},
            'semantics': {...}  # sadece include_semantics=True ise
        }
    """
    nlp = get_nlp()
    doc: Any = nlp(sentence)
    
    preferences = []
    prop_analyzer = None
    
    # Initialize propositional analyzer if needed
    if include_semantics and PROPOSITIONAL_AVAILABLE and TurkishPropositionAnalyzer is not None:
        prop_analyzer = TurkishPropositionAnalyzer()
    
    # Lexicalized -mA compounds (no preference)
    LEXICALIZED_mA = ['yüzme', 'koşma', 'kayma', 'dolma', 'sarma', 'basma']
    
    for sent in doc.sentences:
        for word in sent.words:
            # -DIK eki kontrolü
            if word.upos == 'VERB' and word.text.lower().endswith(('duğu', 'duğum', 'duğun', 'diği', 'diğim', 'dığı', 'tığı', 'tığım')):
                confidence = 0.90
                semantic_note = ""
                
                # Semantic validation
                if prop_analyzer and word.feats and PredicateType is not None:
                    predicate_type = prop_analyzer.analyze_predicate_type(word.feats)
                    if predicate_type == PredicateType.PARTITIVE:
                        confidence = 0.95
                        semantic_note = " [Semantic: partitive → nominal]"
                
                preferences.append({
                    'word': word.text,
                    'type': 'Nominal domain preference (VERB-origin)',
                    'position': word.id,
                    'upos': word.upos,
                    'suggestion': f'Consider NOUN tag (semantic nominal domain){semantic_note}',
                    'confidence': confidence
                })
            
            # -mA eki kontrolü (lexicalized hariç)
            elif word.upos == 'VERB' and word.text.lower().endswith(('ma', 'me')):
                # Lexicalized compound kontrolü
                is_lexicalized = any(word.text.lower().startswith(lex) for lex in LEXICALIZED_mA)
                
                if not is_lexicalized:
                    confidence = 0.80
                    semantic_note = ""
                    
                    # Semantic validation
                    if prop_analyzer and word.feats and PredicateType is not None:
                        predicate_type = prop_analyzer.analyze_predicate_type(word.feats)
                        if predicate_type == PredicateType.HOLISTIC:
                            confidence = 0.85
                            semantic_note = " [Holistic predicate in nominal context]"
                    
                    preferences.append({
                        'word': word.text,
                        'type': 'Nominal domain preference (VERB-origin)',
                        'position': word.id,
                        'upos': word.upos,
                        'suggestion': f'Consider NOUN tag (verbal noun context){semantic_note}',
                        'confidence': confidence
                    })
    
    result = {
        'sentence': sentence,
        'preferences': preferences,
        'summary': {
            'total': len(preferences),
            'strong_preferences': len([p for p in preferences if p['confidence'] >= 0.90]),
            'weak_preferences': len([p for p in preferences if p['confidence'] < 0.90])
        }
    }
    
    # Add semantic analysis if requested
    if include_semantics and PROPOSITIONAL_AVAILABLE and analyze_sentence_with_stanza is not None:
        try:
            semantic_analysis = analyze_sentence_with_stanza(sentence)
            result['semantics'] = semantic_analysis
        except Exception as e:
            result['semantics'] = {'error': str(e)}
    elif include_semantics:
        result['semantics'] = {'error': 'Propositional semantics not available'}
    
    return result


if __name__ == "__main__":
    # Demo
    print("=" * 80)
    print("SIMPLE API DEMO: POS Preferences with Semantic Enhancement")
    print("=" * 80)
    
    test_sentences = [
        ("Ali'nin okuduğu kitap burada.", True),
        ("Yazma defteri aldım.", True),
        ("Yüzme havuzu temiz.", False),
        ("Kuşlar uçar.", True),
    ]
    
    for sentence, show_semantics in test_sentences:
        print(f"\n📝 '{sentence}'")
        print("-" * 80)
        
        result = check_sentence(sentence, include_semantics=show_semantics)
        
        # Show preferences
        if result['preferences']:
            print(f"✓ {len(result['preferences'])} preference(s) detected:")
            for pref in result['preferences']:
                semantic_marker = "🔬" if "[Semantic:" in pref['suggestion'] else "  "
                print(f"  {semantic_marker} {pref['word']}: {pref['confidence']:.0%}")
                print(f"     {pref['suggestion']}")
        else:
            print("  No preferences detected")
        
        # Show semantics if included
        if show_semantics and 'semantics' in result:
            semantics = result.get('semantics', {})
            if 'analyses' in semantics and semantics['analyses']:
                semantic = semantics['analyses'][0]
                pv = semantic['propositional_value']
                print(f"\n  Semantic: {pv['type']} / {pv['predicate_type']} (generic={pv['generic']})")
