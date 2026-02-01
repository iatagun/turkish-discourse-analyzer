"""
Hatalı POS Tagging durumlarında Merkezleme Kuramının yardımını test et
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
import torch

# PyTorch weights_only workaround
_orig_load = torch.load
def _load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_load(*args, **kwargs)
torch.load = _load

import stanza


@dataclass
class Token:
    form: str
    upos: str
    head: int
    deprel: str


@dataclass
class CenteringState:
    forward_centers: List[str]
    backward_center: Optional[str]
    preferred_center: Optional[str]
    pronoun_resolutions: Optional[dict] = None

    def __post_init__(self):
        if self.pronoun_resolutions is None:
            self.pronoun_resolutions = {}


class TransitionType(Enum):
    CONTINUE = "Continue"
    RETAIN = "Retain"
    SMOOTH_SHIFT = "Smooth-Shift"
    ROUGH_SHIFT = "Rough-Shift"


def resolve_pronouns(tokens: List[Token], prev_state: Optional[CenteringState]) -> dict:
    """Zamir çözümlemesi yap - geliştirilmiş sayı uyumu ve mesafe kontrolü
    
    ÖNEMLİ: Sadece POS=PRON olan tokenlar için zamir çözümlemesi yapar!
    """
    turkish_pronouns = {
        'o': {'type': 'personal', 'number': 'singular'},
        'onlar': {'type': 'personal', 'number': 'plural'},
        'bu': {'type': 'demonstrative', 'number': 'singular'},
        'bunlar': {'type': 'demonstrative', 'number': 'plural'},
        'şu': {'type': 'demonstrative', 'number': 'singular'},
        'şunlar': {'type': 'demonstrative', 'number': 'plural'},
    }
    
    def is_plural(word: str) -> bool:
        if word.endswith('ler') or word.endswith('lar'):
            return True
        if word.endswith('lere') or word.endswith('lara'):
            return True
        if word.endswith('lerde') or word.endswith('larda'):
            return True
        return False
    
    resolutions = {}
    
    if prev_state is None or not prev_state.forward_centers:
        return resolutions
    
    for tok in tokens:
        # ⚠️ KRITIK: Sadece PRON etiketli tokenları işle
        if tok.upos != "PRON":
            continue
        
        tok_lower = tok.form.lower()
        if tok_lower in turkish_pronouns:
            pron_info = turkish_pronouns[tok_lower]
            best_match = None
            best_score = -1
            
            for idx, prev_center in enumerate(prev_state.forward_centers):
                score = 0.0
                
                if pron_info['number'] == 'plural':
                    if is_plural(prev_center):
                        score += 10.0
                    else:
                        score += 1.0
                else:
                    if not is_plural(prev_center):
                        score += 8.0
                    else:
                        score += 1.0
                
                position_score = (len(prev_state.forward_centers) - idx) / len(prev_state.forward_centers)
                score += position_score * 3.0
                score += 2.0
                
                if score > best_score:
                    best_score = score
                    best_match = prev_center
            
            if best_match:
                resolutions[tok_lower] = best_match
    
    return resolutions


def compute_forward_centers(tokens: List[Token], pronoun_resolutions: Optional[dict] = None) -> List[str]:
    if pronoun_resolutions is None:
        pronoun_resolutions = {}
    
    salience_weights = {
        "nsubj": 4,
        "obj": 3,
        "obl": 2,
    }
    pos_weights = {
        "PRON": 3,
        "PROPN": 2,
        "NOUN": 1,
    }

    centers = []
    for i, tok in enumerate(tokens):
        tok_lower = tok.form.lower()
        
        if tok_lower in pronoun_resolutions:
            referent = pronoun_resolutions[tok_lower]
            salience = 0.0
            if tok.deprel in salience_weights:
                salience += salience_weights[tok.deprel]
            salience += pos_weights.get("PRON", 3)
            position_weight = 1.0 - (i / max(1, len(tokens)))
            salience += position_weight
            centers.append((referent, salience, i))
            continue
        
        if tok.upos not in {"NOUN", "PROPN", "PRON"}:
            continue
        salience = 0.0
        if tok.deprel in salience_weights:
            salience += salience_weights[tok.deprel]
        if tok.upos in pos_weights:
            salience += pos_weights[tok.upos]
        position_weight = 1.0 - (i / max(1, len(tokens)))
        salience += position_weight
        centers.append((tok_lower, salience, i))

    centers.sort(key=lambda x: (-x[1], x[2]))
    seen = set()
    ordered = []
    for center, _, _ in centers:
        if center not in seen:
            seen.add(center)
            ordered.append(center)
    return ordered[:5]


def compute_transition(prev_state: Optional[CenteringState], current_cf: List[str], pronoun_resolutions: Optional[dict] = None) -> Tuple[Optional[TransitionType], CenteringState]:
    if pronoun_resolutions is None:
        pronoun_resolutions = {}
    
    cp = current_cf[0] if current_cf else None

    if prev_state is None:
        state = CenteringState(forward_centers=current_cf, backward_center=None, preferred_center=cp, pronoun_resolutions=pronoun_resolutions)
        return None, state

    prev_cb = prev_state.backward_center
    cb = None
    for prev_center in prev_state.forward_centers:
        if prev_center in current_cf:
            cb = prev_center
            break

    if cb is None:
        transition = TransitionType.ROUGH_SHIFT
    else:
        if prev_cb == cb and cb == cp:
            transition = TransitionType.CONTINUE
        elif prev_cb == cb and cb != cp:
            transition = TransitionType.RETAIN
        elif prev_cb != cb and cb == cp:
            transition = TransitionType.SMOOTH_SHIFT
        else:
            transition = TransitionType.ROUGH_SHIFT

    state = CenteringState(forward_centers=current_cf, backward_center=cb, preferred_center=cp, pronoun_resolutions=pronoun_resolutions)
    return transition, state


def transition_score(transition: Optional[TransitionType]) -> int:
    if transition is None:
        return 1
    weights = {
        TransitionType.CONTINUE: 3,
        TransitionType.RETAIN: 2,
        TransitionType.SMOOTH_SHIFT: 2,
        TransitionType.ROUGH_SHIFT: 1,
    }
    return weights.get(transition, 0)


def score_parse(tokens: List[Token], prev_state: Optional[CenteringState]) -> Tuple[int, CenteringState]:
    pronoun_resolutions = resolve_pronouns(tokens, prev_state)
    cf = compute_forward_centers(tokens, pronoun_resolutions)
    transition, state = compute_transition(prev_state, cf, pronoun_resolutions)
    return transition_score(transition), state


def print_parse_analysis(name: str, tokens: List[Token], prev_state: Optional[CenteringState]):
    """Parse analizi yazdır"""
    print(f"\n{'='*80}")
    print(f"📊 {name}")
    print(f"{'='*80}")
    
    # Token bilgileri
    print("\nToken Detayları:")
    for tok in tokens:
        print(f"  {tok.form:15} → POS: {tok.upos:6}  DEP: {tok.deprel:10}")
    
    # Zamir çözümlemesi
    pronoun_resolutions = resolve_pronouns(tokens, prev_state)
    if pronoun_resolutions:
        print("\n🔗 Zamir Çözümlemesi:")
        for pron, ref in pronoun_resolutions.items():
            print(f"  • '{pron}' → '{ref}'")
    
    # Forward centers
    cf = compute_forward_centers(tokens, pronoun_resolutions)
    print(f"\nForward Centers (Cf): {cf[:3]}")
    
    # Geçiş analizi
    transition, state = compute_transition(prev_state, cf, pronoun_resolutions)
    score = transition_score(transition)
    
    print(f"\nBackward Center (Cb): {state.backward_center or 'YOK'}")
    print(f"Preferred Center (Cp): {state.preferred_center or 'YOK'}")
    print(f"Geçiş Tipi: {transition.value if transition else 'İLK CÜMLE'}")
    print(f"📈 Centering Skoru: {score}")
    
    return score, state


def main():
    print("🧪 HATALI POS TAGGING'DE MERKEZLEME KURAMI TESTİ")
    print("="*80)
    
    # Test senaryosu: "Ahmet markete gitti. O süt aldı."
    print("\n📖 TEST SENARYOSU:")
    print("Cümle 1: 'Ahmet markete gitti.'")
    print("Cümle 2: 'O süt aldı.'")
    print("\nİki farklı parser karşılaştırması:")
    
    # Cümle 1 - her iki parser için aynı (doğru)
    print("\n" + "─"*80)
    print("CÜMLE 1: 'Ahmet markete gitti.'")
    print("─"*80)
    
    sent1_tokens = [
        Token("Ahmet", "PROPN", 3, "nsubj"),
        Token("markete", "NOUN", 3, "obl"),
        Token("gitti", "VERB", 0, "root"),
    ]
    
    print("\n✅ Her iki parser da bu cümleyi doğru etiketledi:")
    prev_state = None
    score1, state1 = score_parse(sent1_tokens, prev_state)
    print(f"Centering Skoru: {score1}")
    print(f"Cb: {state1.backward_center or 'YOK'}, Cp: {state1.preferred_center}")
    
    # Cümle 2 - Parser A (DOĞRU)
    print("\n" + "─"*80)
    print("CÜMLE 2: 'O süt aldı.'")
    print("─"*80)
    
    sent2_correct = [
        Token("O", "PRON", 3, "nsubj"),      # ✅ Doğru: PRON
        Token("süt", "NOUN", 3, "obj"),
        Token("aldı", "VERB", 0, "root"),
    ]
    
    sent2_wrong = [
        Token("O", "NOUN", 3, "nsubj"),      # ❌ Yanlış: NOUN olarak etiketlemiş
        Token("süt", "NOUN", 3, "obj"),
        Token("aldı", "VERB", 0, "root"),
    ]
    
    score_correct, state_correct = print_parse_analysis(
        "PARSER A (Doğru POS): 'O' → PRON", 
        sent2_correct, 
        state1
    )
    
    score_wrong, state_wrong = print_parse_analysis(
        "PARSER B (Hatalı POS): 'O' → NOUN", 
        sent2_wrong, 
        state1
    )
    
    # Karşılaştırma
    print("\n" + "="*80)
    print("🎯 CENTERING-BASED RERANKING SONUCU")
    print("="*80)
    
    print(f"\nParser A (PRON) Skoru: {score_correct}")
    print(f"Parser B (NOUN) Skoru: {score_wrong}")
    
    if score_correct > score_wrong:
        print("\n✅ Centering Reranking → PARSER A seçildi (DOĞRU!)")
        print("   Sebep: PRON etiketi zamir çözümlemesine izin verdi")
        print("   'O' → 'ahmet' bağlantısı kuruldu")
        print("   Backward Center bulundu → daha yüksek skor")
    elif score_wrong > score_correct:
        print("\n❌ Centering Reranking → PARSER B seçildi (YANLIŞ!)")
        print("   Problem: NOUN etiketi zamir çözümlemesini engelledi")
    else:
        print("\n⚠️  Her iki parser da eşit skor aldı")
    
    print("\n" + "="*80)
    print("📊 DETAYLI KARŞILAŞTIRMA")
    print("="*80)
    
    print("\nParser A (PRON):")
    has_resolution_correct = state_correct.pronoun_resolutions and 'o' in state_correct.pronoun_resolutions
    print(f"  • Zamir çözümlemesi: {has_resolution_correct}")
    if has_resolution_correct and state_correct.pronoun_resolutions:
        print(f"  • 'o' → '{state_correct.pronoun_resolutions['o']}'")
    print(f"  • Backward Center: {state_correct.backward_center or 'YOK'}")
    print(f"  • Geçiş tipi tutarlılığı: {score_correct}/3")
    
    print("\nParser B (NOUN):")
    has_resolution_wrong = state_wrong.pronoun_resolutions and 'o' in state_wrong.pronoun_resolutions
    print(f"  • Zamir çözümlemesi: {has_resolution_wrong}")
    print(f"  • Backward Center: {state_wrong.backward_center or 'YOK'}")
    print(f"  • Geçiş tipi tutarlılığı: {score_wrong}/3")
    
    print("\n💡 SONUÇ:")
    print("Merkezleme kuramı, zamir çözümlemesi sayesinde")
    print("hatalı POS etiketlemelerini tespit edip düzeltebilir!")


if __name__ == "__main__":
    main()
