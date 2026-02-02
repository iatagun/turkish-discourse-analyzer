"""
Türkçeye Uyarlanmış Merkezleme Kuramı (Centering Theory for Turkish)

Bu modül, Grosz, Joshi ve Weinstein'ın (1995) Merkezleme Kuramını
Türkçe dilinin özelliklerine göre uyarlar.

Türkçeye Özgü Adaptasyonlar:
- SOV kelime sırası (Subject-Object-Verb)
- Pro-drop özelliği (düşen zamirler)
- Zengin durum ekleri sistemi
- Serbest kelime sırası
"""

from typing import List, Dict, Optional, Tuple
from enum import Enum


class TransitionType(Enum):
    """Söylem geçiş türleri"""
    CONTINUE = "Continue"      # Cb(U_n) = Cb(U_n-1) = Cp(U_n)
    RETAIN = "Retain"          # Cb(U_n) = Cb(U_n-1) ≠ Cp(U_n)
    SMOOTH_SHIFT = "Smooth-Shift"  # Cb(U_n) ≠ Cb(U_n-1), Cb(U_n) = Cp(U_n)
    ROUGH_SHIFT = "Rough-Shift"    # Cb(U_n) ≠ Cb(U_n-1), Cb(U_n) ≠ Cp(U_n)
    NULL = "Null"              # Cb(U_n) = None


class Entity:
    """Söylem varlığı (discourse entity)"""
    def __init__(self, text: str, grammatical_role: str, case_marker: Optional[str] = None):
        self.text = text
        self.grammatical_role = grammatical_role  # SUBJ, OBJ, IOBJ, vb.
        self.case_marker = case_marker  # -i, -e, -de, -den, vb.
        
    def __repr__(self):
        return f"Entity({self.text}, {self.grammatical_role})"
    
    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self.text == other.text


class Utterance:
    """Söylem birimi (utterance)"""
    def __init__(self, text: str, entities: List[Entity]):
        self.text = text
        self.entities = entities
        self.cf_list: List[Entity] = []  # Forward-looking centers
        self.cb: Optional[Entity] = None  # Backward-looking center
        self.cp: Optional[Entity] = None  # Preferred center
        
    def __repr__(self):
        return f"Utterance('{self.text}', entities={len(self.entities)})"


class TurkishCenteringTheory:
    """Türkçe için Merkezleme Kuramı"""
    
    # Türkçe dilbilgisel rollerin öncelik sıralaması
    ROLE_RANKING = {
        'SUBJ': 1,    # Özne (en yüksek öncelik)
        'OBJ': 2,     # Nesne
        'IOBJ': 3,    # Dolaylı nesne
        'POSS': 4,    # İyelik
        'COMP': 5,    # Tümleç
        'ADJ': 6,     # Sıfat
        'OTHER': 7    # Diğer
    }
    
    def __init__(self):
        self.discourse: List[Utterance] = []
        
    def rank_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        Varlıkları Türkçe dilbilgisel rollere göre sıralar.
        
        Türkçe için sıralama:
        SUBJ > OBJ > IOBJ > POSS > COMP > ADJ > OTHER
        """
        return sorted(entities, key=lambda e: self.ROLE_RANKING.get(e.grammatical_role, 999))
    
    def compute_cf_list(self, utterance: Utterance) -> List[Entity]:
        """
        Forward-looking centers listesini hesaplar.
        Cf(U_n) = varlıkları dilbilgisel role göre sıralı liste
        """
        return self.rank_entities(utterance.entities)
    
    def compute_cb(self, current_utterance: Utterance, 
                   previous_utterance: Optional[Utterance]) -> Optional[Entity]:
        """
        Backward-looking center'ı hesaplar.
        Cb(U_n) = Cp(U_n-1) eğer Cp(U_n-1) ∈ Cf(U_n)
        
        Not: Zamir çözümleme analyze_utterance()'da yapılır
        """
        if previous_utterance is None:
            return None
            
        if previous_utterance.cp is None:
            return None
            
        # Cp(U_n-1) şu anki utterance'da var mı? (zamirler zaten resolve edilmiş)
        current_entities_text = [e.text for e in current_utterance.entities]
        if previous_utterance.cp.text in current_entities_text:
            for entity in current_utterance.entities:
                if entity.text == previous_utterance.cp.text:
                    return entity
        
        # Örtük özne (pro-drop): Özne yoksa ama önceki Cp özne ise
        has_subject = any(e.grammatical_role == 'SUBJ' for e in current_utterance.entities)
        if not has_subject and previous_utterance.cp.grammatical_role == 'SUBJ':
            return Entity(previous_utterance.cp.text, 'SUBJ', previous_utterance.cp.case_marker)
        
        return None
    
    def compute_cp(self, utterance: Utterance) -> Optional[Entity]:
        """
        Preferred center'ı hesaplar.
        Cp(U_n) = Cf(U_n) listesinin en yüksek öncelikli elemanı
        """
        if not utterance.cf_list:
            return None
        return utterance.cf_list[0]
    
    def determine_transition(self, current_utterance: Utterance,
                           previous_utterance: Optional[Utterance]) -> TransitionType:
        """
        Söylem geçiş türünü belirler.
        
        Geçiş Kuralları:
        - CONTINUE: Cb(U_n) = Cb(U_n-1) = Cp(U_n)
        - RETAIN: Cb(U_n) = Cb(U_n-1) ≠ Cp(U_n)
        - SMOOTH-SHIFT: Cb(U_n) ≠ Cb(U_n-1), Cb(U_n) = Cp(U_n)
        - ROUGH-SHIFT: Cb(U_n) ≠ Cb(U_n-1), Cb(U_n) ≠ Cp(U_n)
        - NULL: Hiç entity yoksa veya ilk utterance
        """
        # Hiç entity yoksa NULL
        if not current_utterance.entities:
            return TransitionType.NULL
            
        # İlk utterance ise
        if previous_utterance is None:
            if current_utterance.cb == current_utterance.cp:
                return TransitionType.SMOOTH_SHIFT
            else:
                return TransitionType.ROUGH_SHIFT
        
        # Cb = None ama önceki utterance var → Konu değişti
        if current_utterance.cb is None:
            # Önceki Cp varsa (bir konu vardı) ama şimdi Cb yok → ROUGH-SHIFT
            if previous_utterance.cp is not None:
                return TransitionType.ROUGH_SHIFT
            # Her iki tarafta da Cp/Cb yok → NULL
            return TransitionType.NULL
        
        # Önceki Cb yoksa
        if previous_utterance.cb is None:
            if current_utterance.cb == current_utterance.cp:
                return TransitionType.SMOOTH_SHIFT
            else:
                return TransitionType.ROUGH_SHIFT
        
        # Normal Centering kuralları
        cb_same = current_utterance.cb == previous_utterance.cb
        cb_cp_same = current_utterance.cb == current_utterance.cp
        
        if cb_same and cb_cp_same:
            return TransitionType.CONTINUE
        elif cb_same and not cb_cp_same:
            return TransitionType.RETAIN
        elif not cb_same and cb_cp_same:
            return TransitionType.SMOOTH_SHIFT
        else:
            return TransitionType.ROUGH_SHIFT
    
    def analyze_utterance(self, utterance: Utterance) -> Tuple[TransitionType, Dict]:
        """
        Bir söylem birimini analiz eder ve merkezleme bilgilerini hesaplar.
        
        Returns:
            (TransitionType, centering_info dict)
        """
        previous_utterance = self.discourse[-1] if self.discourse else None
        
        # Türkçe zamirleri
        turkish_pronouns = {'o', 'bu', 'şu', 'bunu', 'şunu', 'onu', 'bunun', 'şunun', 'onun'}
        
        # Zamirleri önceki Cp ile değiştir (resolve et)
        if previous_utterance and previous_utterance.cp:
            resolved_entities = []
            for entity in utterance.entities:
                if entity.text.lower() in turkish_pronouns:
                    # Zamiri önceki Cp ile değiştir
                    # ÖNEMLI: Zamir genelde özne olduğu için önceki Cp'nin role'ünü kullan
                    new_role = entity.grammatical_role if entity.grammatical_role in ['SUBJ', 'OBJ'] else previous_utterance.cp.grammatical_role
                    resolved_entities.append(Entity(previous_utterance.cp.text, new_role, entity.case_marker))
                else:
                    resolved_entities.append(entity)
            utterance.entities = resolved_entities
        
        # Cf listesini hesapla
        utterance.cf_list = self.compute_cf_list(utterance)
        
        # Cp'yi hesapla
        utterance.cp = self.compute_cp(utterance)
        
        # Cb'yi hesapla
        utterance.cb = self.compute_cb(utterance, previous_utterance)
        
        # Geçiş türünü belirle
        transition = self.determine_transition(utterance, previous_utterance)
        
        # Utterance'ı discourse'a ekle
        self.discourse.append(utterance)
        
        centering_info = {
            'cf_list': utterance.cf_list,
            'cb': utterance.cb,
            'cp': utterance.cp,
            'transition': transition
        }
        
        return transition, centering_info
    
    def get_discourse_coherence_score(self) -> float:
        """
        Söylem tutarlılık skorunu hesaplar.
        
        Continue > Retain > Smooth-Shift > Rough-Shift
        
        Returns:
            0.0 - 1.0 arası normalleştirilmiş skor
        """
        if len(self.discourse) < 2:
            return 1.0
        
        transition_scores = {
            TransitionType.CONTINUE: 4,
            TransitionType.RETAIN: 3,
            TransitionType.SMOOTH_SHIFT: 2,
            TransitionType.ROUGH_SHIFT: 1,
            TransitionType.NULL: 2
        }
        
        total_score = 0
        max_possible_score = 0
        
        for i in range(1, len(self.discourse)):
            transition = self.determine_transition(self.discourse[i], self.discourse[i-1])
            total_score += transition_scores[transition]
            max_possible_score += 4  # CONTINUE'nun skoru
        
        return total_score / max_possible_score if max_possible_score > 0 else 0.0
    
    def reset(self):
        """Söylem analizini sıfırlar"""
        self.discourse = []


def analyze_turkish_discourse(utterances_data: List[Dict]) -> List[Dict]:
    """
    Türkçe söylem dizisini analiz eder.
    
    Args:
        utterances_data: Her biri {'text': str, 'entities': [...]} içeren sözlük listesi
        
    Returns:
        Her utterance için merkezleme analizi içeren liste
    """
    ct = TurkishCenteringTheory()
    results = []
    
    for utt_data in utterances_data:
        entities = [
            Entity(e['text'], e['role'], e.get('case'))
            for e in utt_data['entities']
        ]
        utterance = Utterance(utt_data['text'], entities)
        transition, info = ct.analyze_utterance(utterance)
        
        results.append({
            'text': utt_data['text'],
            'cf_list': [e.text for e in info['cf_list']],
            'cb': info['cb'].text if info['cb'] else None,
            'cp': info['cp'].text if info['cp'] else None,
            'transition': transition.value
        })
    
    return results
