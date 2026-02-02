"""
API Integration: Propositional Semantics + POS Preferences

Bu modül önermesel semantik analizini mevcut API'ye entegre eder.
"""

from typing import Dict, Any, List
import sys
from pathlib import Path

# Add src to path
_src_path = Path(__file__).parent.parent / 'src'
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

try:
    from propositional_semantics import (  # type: ignore
        TurkishPropositionAnalyzer,
        analyze_sentence_with_stanza,
        PredicateType,
        PropositionType
    )
    PROPOSITIONAL_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PROPOSITIONAL_AVAILABLE = False
    TurkishPropositionAnalyzer = None  # type: ignore
    analyze_sentence_with_stanza = None  # type: ignore
    PredicateType = None  # type: ignore
    PropositionType = None  # type: ignore


def check_sentence_enhanced(sentence: str) -> Dict[str, Any]:
    """
    Geliştirilmiş cümle kontrolü: POS preferences + Propositional semantics
    
    Args:
        sentence: Türkçe cümle
        
    Returns:
        {
            'pos_analysis': {...},          # Mevcut POS preference analizi
            'propositional': {...},         # YENİ: Önermesel semantik
            'theoretical_explanation': str  # YENİ: Teorik açıklama
        }
    """
    from api.main import check_sentence
    
    # Mevcut POS analizi
    pos_result = check_sentence(sentence)
    
    result = {
        'sentence': sentence,
        'pos_analysis': pos_result
    }
    
    # Önermesel semantik analizi ekle
    if PROPOSITIONAL_AVAILABLE:
        if callable(analyze_sentence_with_stanza):
            try:
                prop_analysis: Dict[str, Any] = analyze_sentence_with_stanza(sentence)  # type: ignore
                result['propositional'] = prop_analysis
                
                # Teorik açıklama oluştur
                if prop_analysis.get('analyses'):
                    analysis = prop_analysis['analyses'][0]
                    pv = analysis['propositional_value']
                    
                    explanation = f"""
ÖNERMESEL SEMANTİK ANALİZ:
• Önerme Tipi: {pv['type']} ({'genel-geçer' if pv['generic'] else 'zamana gönderimli'})
• Yüklem Tipi: {pv['predicate_type']} ({'özellik tümcesi' if pv['predicate_type'] == 'bütüncül' else 'olay tümcesi'})
• Doğrulanabilirlik: {pv['verifiable']:.0%}

TEORİK BAĞLANTI:
{_create_theoretical_connection(pos_result, pv)}
"""
                    result['theoretical_explanation'] = explanation.strip()
            except Exception as e:
                result['propositional'] = {'error': str(e)}
        else:
            result['propositional'] = {'error': 'Propositional analysis function not available'}
    else:
        result['propositional'] = {
            'error': 'Propositional semantics module not available'
        }
    
    return result


def _create_theoretical_connection(pos_result: Dict, prop_value: Dict) -> str:
    """POS preference ile önermesel semantik arasındaki bağlantıyı açıkla"""
    
    connections = []
    
    # -DIK eki bağlantısı
    for error in pos_result.get('errors', []):
        if 'DIK' in error.get('type', ''):
            if prop_value['predicate_type'] == 'parçalı':
                connections.append(
                    "✓ -DIK eki → Parçalı yüklem marker'ı → Özgüllük kazandırır → Nominal domain"
                )
    
    # Generic vs specific
    if prop_value.get('generic'):
        connections.append(
            "✓ Generic kodlama → Bütüncül yüklem → Analitik önerme (genel-geçer)"
        )
    else:
        connections.append(
            "✓ Özgül kodlama → Parçalı yüklem → Sentetik önerme (zamana bağlı)"
        )
    
    # Predicate type açıklaması
    if prop_value['predicate_type'] == 'bütüncül':
        connections.append(
            "• Bütüncül yüklem: Zamanda bir noktaya oturmaz, özellik bildirir"
        )
    else:
        connections.append(
            "• Parçalı yüklem: Zamanda bir noktaya oturur, olay bildirir"
        )
    
    return '\n'.join(connections) if connections else 'Teorik bağlantı tespit edilmedi'


def demo_enhanced_analysis():
    """Geliştirilmiş analiz demo"""
    
    test_cases = [
        "Ali'nin okuduğu kitap burada.",     # -DIK eki + parçalı yüklem
        "Kuşlar uçar.",                       # Generic + bütüncül
        "Yazma defteri aldım.",               # -mA eki preference
        "Yüzme havuzu temiz.",                # -mA eki lexicalized
    ]
    
    print("=" * 80)
    print("GELİŞTİRİLMİŞ ANALİZ: POS Preferences + Önermesel Semantik")
    print("=" * 80)
    
    for sentence in test_cases:
        print(f"\n📝 '{sentence}'")
        print("-" * 80)
        
        result = check_sentence_enhanced(sentence)
        
        # POS preferences
        pos = result['pos_analysis']
        if pos.get('errors'):
            print(f"\n🔍 POS Preferences tespit edildi: {len(pos['errors'])}")
            for err in pos['errors']:
                print(f"   • {err['word']}: {err['type']} (güven: {err['confidence']:.0%})")
        else:
            print("\n✅ POS preferences yok")
        
        # Önermesel semantik
        if 'theoretical_explanation' in result:
            print(f"\n{result['theoretical_explanation']}")
        elif 'error' in result.get('propositional', {}):
            print(f"\n⚠️  Önermesel analiz: {result['propositional']['error']}")


if __name__ == "__main__":
    demo_enhanced_analysis()
