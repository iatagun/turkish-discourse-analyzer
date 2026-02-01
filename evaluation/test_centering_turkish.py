"""
Merkezleme kuramı Türkçe örnek cümlelerle test
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

import torch
import stanza


# Work around PyTorch 2.6+ weights_only issue
_orig_load = torch.load

def _load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_load(*args, **kwargs)


torch.load = _load


@dataclass
class Token:
    form: str
    upos: str
    deprel: str
    head_idx: int


class TransitionType(Enum):
    CONTINUE = "Continue"
    RETAIN = "Retain"
    SMOOTH_SHIFT = "Smooth-Shift"
    ROUGH_SHIFT = "Rough-Shift"


@dataclass
class CenteringState:
    forward_centers: List[str]
    backward_center: Optional[str]
    preferred_center: Optional[str]
    transition: Optional[TransitionType]
    pronoun_resolutions: Optional[dict] = None  # zamir -> referans eşleştirmesi

    def __post_init__(self):
        if self.pronoun_resolutions is None:
            self.pronoun_resolutions = {}


def parse_sentence(nlp, text: str) -> List[Token]:
    """Cümleyi Stanza ile ayrıştır"""
    doc = nlp(text)
    if not doc.sentences:
        return []
    
    sent = doc.sentences[0]
    tokens = []
    for word in sent.words:
        tokens.append(Token(
            form=word.text,
            upos=word.upos,
            deprel=word.deprel,
            head_idx=word.head
        ))
    return tokens


def resolve_pronouns(tokens: List[Token], prev_state: Optional[CenteringState]) -> dict:
    """Zamir çözümlemesi yap - geliştirilmiş sayı uyumu ve mesafe kontrolü"""
    turkish_pronouns = {
        'o': {'type': 'personal', 'number': 'singular'},
        'onlar': {'type': 'personal', 'number': 'plural'},
        'bu': {'type': 'demonstrative', 'number': 'singular'},
        'bunlar': {'type': 'demonstrative', 'number': 'plural'},
        'şu': {'type': 'demonstrative', 'number': 'singular'},
        'şunlar': {'type': 'demonstrative', 'number': 'plural'},
        'kendisi': {'type': 'reflexive', 'number': 'singular'},
        'kendileri': {'type': 'reflexive', 'number': 'plural'},
    }
    
    # Türkçe çoğul ekleri ve özel durumlar
    def is_plural(word: str) -> bool:
        """Türkçe kelimede çoğul kontrolü"""
        # -ler, -lar ekleri
        if word.endswith('ler') or word.endswith('lar'):
            return True
        # -e/-a ile biten haller (öğrencilere, çocuklara gibi)
        if word.endswith('lere') or word.endswith('lara'):
            return True
        # -de/-da ile biten haller (öğrencilerde, çocuklarda)
        if word.endswith('lerde') or word.endswith('larda'):
            return True
        return False
    
    resolutions = {}
    
    if prev_state is None or not prev_state.forward_centers:
        return resolutions
    
    for tok in tokens:
        tok_lower = tok.form.lower()
        if tok_lower in turkish_pronouns:
            pron_info = turkish_pronouns[tok_lower]
            best_match = None
            best_score = -1
            
            # Tüm önceki merkezleri skorla
            for idx, prev_center in enumerate(prev_state.forward_centers):
                score = 0.0
                
                # Sayı uyumu (en önemli)
                if pron_info['number'] == 'plural':
                    if is_plural(prev_center):
                        score += 10.0  # Çoğul zamir - çoğul isim: güçlü eşleşme
                    else:
                        score += 1.0   # Çoğul zamir - tekil isim: zayıf eşleşme
                else:  # singular
                    if not is_plural(prev_center):
                        score += 8.0   # Tekil zamir - tekil isim: güçlü eşleşme
                    else:
                        score += 1.0   # Tekil zamir - çoğul isim: zayıf eşleşme
                
                # Salience skoru (forward centers listesinde önde olanlar daha önemli)
                # Ama semantic role için: object/oblique çoğul zamirlerde tercih edilebilir
                position_score = (len(prev_state.forward_centers) - idx) / len(prev_state.forward_centers)
                score += position_score * 3.0
                
                # Mesafe faktörü (yakın geçmişte geçenler tercih edilir)
                # Bu basit versiyonda sadece önceki cümle var, ama genişletilebilir
                score += 2.0
                
                if score > best_score:
                    best_score = score
                    best_match = prev_center
            
            if best_match:
                resolutions[tok_lower] = best_match
    
    return resolutions


def compute_forward_centers(tokens: List[Token], pronoun_resolutions: Optional[dict] = None) -> List[Tuple[str, float]]:
    """Forward centers (Cf) hesapla - ağırlıklarla birlikte döndür"""
    if pronoun_resolutions is None:
        pronoun_resolutions = {}
    
    salience_weights = {
        "nsubj": 4,
        "obj": 3,
        "obl": 2,
        "iobj": 2,
        "nmod": 1,
    }
    pos_weights = {
        "PRON": 3,
        "PROPN": 2,
        "NOUN": 1,
    }
    
    centers = []
    for i, tok in enumerate(tokens):
        tok_lower = tok.form.lower()
        
        # Zamir çözümlemesi varsa, referansı kullan
        if tok_lower in pronoun_resolutions:
            referent = pronoun_resolutions[tok_lower]
            # Hem zamiri hem referansı ekle
            salience = 0.0
            if tok.deprel in salience_weights:
                salience += salience_weights[tok.deprel]
            salience += pos_weights.get("PRON", 3)
            position_weight = 1.0 - (i / max(1, len(tokens)))
            salience += position_weight
            # Referansı da forward centers'a ekle
            centers.append((referent, salience, i))
            continue
        
        if tok.upos not in {"NOUN", "PROPN", "PRON"}:
            continue
        
        salience = 0.0
        
        # Bağımlılık ilişkisi ağırlığı
        if tok.deprel in salience_weights:
            salience += salience_weights[tok.deprel]
        
        # POS ağırlığı
        if tok.upos in pos_weights:
            salience += pos_weights[tok.upos]
        
        # Konum ağırlığı (önce gelenler daha önemli)
        position_weight = 1.0 - (i / max(1, len(tokens)))
        salience += position_weight
        
        centers.append((tok_lower, salience, i))
    
    # Salience'a göre sırala
    centers.sort(key=lambda x: (-x[1], x[2]))
    
    # Benzersiz merkezler
    seen = set()
    unique_centers = []
    for form, sal, _ in centers:
        if form not in seen:
            seen.add(form)
            unique_centers.append((form, sal))
    
    return unique_centers[:5]


def compute_transition(prev_state: Optional[CenteringState], current_cf: List[str], pronoun_resolutions: Optional[dict] = None) -> Tuple[Optional[TransitionType], CenteringState]:
    """Centering geçişini hesapla"""
    if pronoun_resolutions is None:
        pronoun_resolutions = {}
    
    cp = current_cf[0] if current_cf else None
    
    if prev_state is None:
        state = CenteringState(
            forward_centers=current_cf,
            backward_center=None,
            preferred_center=cp,
            transition=None,
            pronoun_resolutions=pronoun_resolutions
        )
        return None, state
    
    # Backward center (Cb) hesapla
    prev_cb = prev_state.backward_center
    cb = None
    for prev_center in prev_state.forward_centers:
        if prev_center in current_cf:
            cb = prev_center
            break
    
    # Geçiş tipini belirle
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
    
    state = CenteringState(
        forward_centers=current_cf,
        backward_center=cb,
        preferred_center=cp,
        transition=transition,
        pronoun_resolutions=pronoun_resolutions
    )
    
    return transition, state


def analyze_discourse(nlp, sentences: List[str]):
    """Söylem analizi yap"""
    print("=" * 80)
    print("MERKEZLEME KURAMI ANALİZİ")
    print("=" * 80)
    
    prev_state = None
    
    for i, sent_text in enumerate(sentences):
        print(f"\n{'─' * 80}")
        print(f"CÜMLE {i + 1}: {sent_text}")
        print(f"{'─' * 80}")
        
        # Ayrıştır
        tokens = parse_sentence(nlp, sent_text)
        
        # Zamir çözümlemesi yap
        pronoun_resolutions = resolve_pronouns(tokens, prev_state)
        
        # Forward centers hesapla (zamir çözümlemesiyle)
        cf_with_scores = compute_forward_centers(tokens, pronoun_resolutions)
        cf = [center for center, _ in cf_with_scores]
        
        # Zamir çözümlemelerini göster
        if pronoun_resolutions:
            print("\n🔗 Zamir Çözümlemesi:")
            for pronoun, referent in pronoun_resolutions.items():
                print(f"  • '{pronoun}' → '{referent}'")
        
        print("\nForward Centers (Cf) - Salience skorlarıyla:")
        for center, score in cf_with_scores:
            print(f"  • {center:15} → {score:.2f}")
        
        # Geçiş analizi
        transition, state = compute_transition(prev_state, cf, pronoun_resolutions)
        
        if prev_state is not None:
            print(f"\nBackward Center (Cb): {state.backward_center or 'YOK'}")
            print(f"Preferred Center (Cp): {state.preferred_center or 'YOK'}")
            print(f"\nGeçiş Tipi: {transition.value if transition else 'İLK CÜMLE'}")
            
            # Geçiş açıklaması
            if transition == TransitionType.CONTINUE:
                print("  → Merkez devam ediyor (en tutarlı)")
            elif transition == TransitionType.RETAIN:
                print("  → Merkez korunuyor ama odak değişiyor")
            elif transition == TransitionType.SMOOTH_SHIFT:
                print("  → Yumuşak geçiş (merkez değişiyor ama tahmin edilebilir)")
            elif transition == TransitionType.ROUGH_SHIFT:
                print("  → Sert geçiş (beklenmeyen merkez değişimi)")
        else:
            print(f"\nPreferred Center (Cp): {state.preferred_center or 'YOK'}")
            print("\nGeçiş Tipi: İLK CÜMLE (merkez oluşturuluyor)")
        
        prev_state = state
    
    print("\n" + "=" * 80)


def main():
    print("Stanza Türkçe modeli yükleniyor...")
    stanza.download("tr", verbose=False)
    nlp = stanza.Pipeline("tr", processors="tokenize,pos,lemma,depparse", verbose=False)
    
    # Örnek söylem 1: Tutarlı merkez
    print("\n\n📖 ÖRNEK 1: TUTARLI SÖYLEM (Center Continuation)")
    sentences1 = [
        "Ahmet dün markete gitti.",
        "O süt ve ekmek aldı.",
        "Sonra eve döndü."
    ]
    analyze_discourse(nlp, sentences1)
    
    # Örnek söylem 2: Merkez değişimi
    print("\n\n📖 ÖRNEK 2: MERKEZ DEĞİŞİMİ (Shift)")
    sentences2 = [
        "Ayşe kitap okuyor.",
        "Ali müzik dinliyor.",
        "Hava çok güzel."
    ]
    analyze_discourse(nlp, sentences2)
    
    # Örnek söylem 3: Karmaşık ilişkiler
    print("\n\n📖 ÖRNEK 3: KARMAŞIK SÖYLEM")
    sentences3 = [
        "Öğretmen öğrencilere soru sordu.",
        "Onlar cevap vermeye çalıştılar.",
        "Sınıf çok sessizdi.",
        "Öğretmen gülümsedi."
    ]
    analyze_discourse(nlp, sentences3)


if __name__ == "__main__":
    main()
