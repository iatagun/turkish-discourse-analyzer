"""
Minimalist Program Teorisi ile POS Tagging Hata Tespiti

Bu modül, Minimalist Program'ın temel prensiplerini kullanarak
POS tagging hatalarını tespit eder:

- Numeration (Sayaç): Lexical items ve kullanım sayıları
- İkililik İlkesi: Binary branching [A[B,C]]
- Operasyonlar: Select → Merge → Move
- Trace Teorisi: Hareket edilen öğelerin izi
- Türetim: Dağıtım → Mantıksal Biçim

Stratejik İki Aşama:
1️⃣ POS + dependency → Aday hatalar
2️⃣ Numeration + move denetimi → Gerçek hatalar

Referans: Chomsky (1995) - The Minimalist Program
"""

from typing import List, Dict, Optional, Tuple, Set, Any
from dataclasses import dataclass
from enum import Enum
import re


class POSErrorType(Enum):
    """POS hata türleri (Minimalist teori bağlamında)"""
    # Kesin yakalananlar
    NOUN_VERB_CONFUSION = "NOUN ↔ VERB"  # -DIK, -mA, -Iş türetmeleri
    PRON_DET_CONFUSION = "PRON ↔ DET"    # Pro-drop + trace
    ADJ_NOUN_CONFUSION = "ADJ ↔ NOUN"    # Adlaşmış sıfatlar
    SUBJECT_OBJECT_MISLABEL = "SUBJ ↔ OBJ"  # Argüman yapısı hataları
    
    # Dolaylı yakalananlar
    ADV_ADJ_CONFUSION = "ADV ↔ ADJ"
    TOPIC_ERROR = "TOPIC error"
    DISCOURSE_SYNTAX_CLASH = "Discourse-Syntax clash"


@dataclass(frozen=True)
class LexicalItem:
    """Lexical item (numeration'da kullanılır)"""
    word: str
    pos: str
    morphology: tuple  # Morfolojik özellikler (tuple for hashability)
    features: tuple = ()  # Feature tuples for hashability
    
    def __repr__(self):
        return f"LexItem({self.word}, {self.pos}, {list(self.morphology)})"
    
    def __hash__(self):
        return hash((self.word, self.pos, self.morphology, self.features))
    
    def __eq__(self, other):
        if not isinstance(other, LexicalItem):
            return False
        return (self.word == other.word and 
                self.pos == other.pos and 
                self.morphology == other.morphology)


@dataclass
class SelectionStep:
    """
    Bir SELECT operasyonu kaydı
    
    Minimalist Program'da türetim: SELECT → MERGE → MOVE
    Her adım kaydedilir ve doğrulanır
    """
    item: LexicalItem
    step_number: int
    remaining_count: int  # Seçimden sonra kalan sayı
    
    def __repr__(self):
        return f"Step{self.step_number}: SELECT({self.item.word})"


@dataclass
class SelectionHistory:
    """
    Tüm SELECT operasyonlarının geçmişi
    
    Bu, türetimin hangi sırada gerçekleştiğini gösterir.
    Hata tespiti için kritik: Yanlış sıra → Yanlış türetim
    """
    steps: List[SelectionStep]
    
    def __init__(self):
        self.steps = []
    
    def add_selection(self, item: LexicalItem, step_number: int, remaining: int):
        """Bir SELECT işlemini kaydet"""
        self.steps.append(SelectionStep(item, step_number, remaining))
    
    def get_selection_order(self) -> List[str]:
        """Seçim sırasını döndür"""
        return [step.item.word for step in self.steps]
    
    def validate_selection_order(self) -> List[Dict]:
        """
        Seçim sırasının geçerliliğini kontrol et
        
        Minimalist kurallar:
        - Fiil önce seçilmeli (theta-grid için)
        - Argümanlar sonra (theta-role alırlar)
        - Fonksiyonel kategoriler en son (C, T, vb.)
        
        Sıra: V → (NP/DP objects) → (NP/DP subjects) → T → C
        """
        errors = []
        
        if not self.steps:
            return errors
        
        # Kural 1: İlk seçim VERB olmalı
        first_item = self.steps[0].item
        
        if first_item.pos not in ['VERB']:
            error_msg = f"First selection should be VERB for theta-grid, but got {first_item.pos} ('{first_item.word}')"
            errors.append({
                'type': 'SELECTION_ORDER_ERROR',
                'reason': error_msg,
                'confidence': 0.9
            })
        
        # Kural 2: VERB'den sonra arguments (NOUN, PROPN)
        # VERB'den önce argument varsa hata
        verb_index = None
        for i, step in enumerate(self.steps):
            if step.item.pos == 'VERB':
                verb_index = i
                break
        
        if verb_index is not None and verb_index > 0:
            # VERB'den önce seçilen itemler
            for i in range(verb_index):
                pre_verb_item = self.steps[i].item
                if pre_verb_item.pos in ['NOUN', 'PROPN']:
                    error_msg = f"Argument '{pre_verb_item.word}' ({pre_verb_item.pos}) selected before VERB - violates theta-role assignment order"
                    errors.append({
                        'type': 'SELECTION_ORDER_ERROR',
                        'item': pre_verb_item,
                        'reason': error_msg,
                        'confidence': 0.9
                    })
        
        return errors


@dataclass
class Numeration:
    """
    Numeration (Sayaç): Lexical items kümesi ve kullanım sayıları
    
    Örnek: {"kitap": 1, "oku": 1, "Ali": 1}
    Türkçe: {"kitabı": 1, "okudu": 1, "Ali": 1}
    """
    items: Dict[LexicalItem, int]  # LexItem -> kullanım sayısı
    selection_history: SelectionHistory
    
    def __init__(self, items: Dict[LexicalItem, int]):
        self.items = items
        self.selection_history = SelectionHistory()
    
    def is_empty(self) -> bool:
        """Tüm lexemler sıfır olduğunda N boş küme"""
        return all(count == 0 for count in self.items.values())
    
    def select(self, item: LexicalItem) -> bool:
        """
        Select operasyonu: Bir lexical item'ı seç ve sayacı azalt
        
        Returns:
            True if selection successful, False otherwise
        """
        if self.items.get(item, 0) > 0:
            self.items[item] -= 1
            step_number = len(self.selection_history.steps) + 1
            self.selection_history.add_selection(item, step_number, self.items[item])
            return True
        return False
    
    def get_selection_history(self) -> SelectionHistory:
        """Seçim geçmişini döndür"""
        return self.selection_history
    
    def compare_type(self, other: 'Numeration') -> bool:
        """
        İki numeration aynı türde mi?
        Farklı türden numerationlar karşılaştırılamaz!
        
        Örnek:
        - "Ali geldi." → Type A
        - "Ayşe Ali'nin geldiğini söyledi." → Type B (embedded)
        - Type A ≠ Type B
        """
        # Basitleştirilmiş: Lexical item sayısı ve komplekslik
        if len(self.items) != len(other.items):
            return False
        
        # Embedded clause varlığını kontrol (gerund -DIK, -mA, vb.)
        self_has_embedded = any(
            '-DIK' in item.morphology or '-mA' in item.morphology 
            for item in self.items.keys()
        )
        other_has_embedded = any(
            '-DIK' in item.morphology or '-mA' in item.morphology 
            for item in other.items.keys()
        )
        
        return self_has_embedded == other_has_embedded


@dataclass
class SyntacticNode:
    """
    Sözdizimsel düğüm (ikililik ilkesine uygun)
    [Head [Complement, Specifier]]
    """
    label: str  # VP, NP, TP, vb.
    head: Optional['SyntacticNode'] = None
    complement: Optional['SyntacticNode'] = None
    specifier: Optional['SyntacticNode'] = None
    terminal: Optional[LexicalItem] = None  # Leaf node
    trace: Optional['SyntacticNode'] = None  # Hareket izi
    moved_from: Optional[str] = None  # Hangi pozisyondan hareket etti
    
    def __repr__(self):
        if self.terminal:
            return f"[{self.terminal.word}]"
        return f"[{self.label}]"
    
    def is_binary(self) -> bool:
        """İkililik ilkesine uygun mu?"""
        children = [c for c in [self.head, self.complement, self.specifier] if c is not None]
        return len(children) <= 2


@dataclass
class Movement:
    """
    Move operasyonu kaydı
    Örnek: "kitabı Ali okudu" → "kitabı" OBJECT pozisyonundan TOPIC'e hareket
    """
    element: LexicalItem
    from_position: str  # "OBJECT", "SUBJECT", vb.
    to_position: str    # "TOPIC", "FOCUS", vb.
    trace_index: int
    
    def requires_trace(self) -> bool:
        """Trace gerektirir mi?"""
        # A-movement (argüman hareketi) trace gerektirir
        return self.from_position in ["OBJECT", "SUBJECT", "INDIRECT_OBJECT"]


class MinimalistPOSErrorDetector:
    """
    Minimalist Program teorisi ile POS hata tespiti
    
    İki aşamalı yaklaşım:
    1️⃣ Aşama 1: POS + dependency analizi → Aday hatalar
    2️⃣ Aşama 2: Numeration + movement denetimi → Gerçek hatalar
    """
    
    # Türkçe nominal türetme ekleri (NOUN ↔ VERB)
    NOMINAL_SUFFIXES = ['-DIK', '-mA', '-Iş', '-mAk', '-AcAK']
    
    # Türkçe adlaşmış sıfat işaretleri
    ADJECTIVAL_NOUNS = ['güzel', 'iyi', 'kötü', 'büyük', 'küçük']  # Genişletilebilir
    
    def __init__(self):
        self.candidate_errors: List[Dict] = []
        self.confirmed_errors: List[Dict] = []
        
    # ========== AŞAMA 1: POS + Dependency Analizi ==========
    
    def detect_noun_verb_confusion(self, item: LexicalItem, context: List[LexicalItem]) -> Optional[Dict]:
        """
        NOUN ↔ VERB karışıklığı tespiti
        
        Hedef: -DIK, -mA, -Iş gibi nominal türetmeler
        
        Örnek:
        - "okuduğum" → VERB olarak etiketlenmiş ama NOUN olmalı (gerundive)
        - "gelme" → VERB ama NOUN (nominal infinitive)
        """
        # Nominal ek varsa ama VERB olarak etiketlenmişse
        has_nominal_suffix = any(suffix in item.morphology for suffix in self.NOMINAL_SUFFIXES)
        
        if has_nominal_suffix and item.pos == 'VERB':
            return {
                'type': POSErrorType.NOUN_VERB_CONFUSION,
                'item': item,
                'expected_pos': 'NOUN',
                'found_pos': 'VERB',
                'reason': f'Nominal suffix detected: {[s for s in self.NOMINAL_SUFFIXES if s in item.morphology]}',
                'confidence': 0.9  # Yüksek güven
            }
        
        # Fiil eki yok ama VERB olarak etiketlenmişse
        has_verb_features = any(feat in item.morphology for feat in ['PAST', 'PRES', 'FUT', 'AOR'])
        if item.pos == 'VERB' and not has_verb_features and not has_nominal_suffix:
            return {
                'type': POSErrorType.NOUN_VERB_CONFUSION,
                'item': item,
                'expected_pos': 'NOUN',
                'found_pos': 'VERB',
                'reason': 'No verbal features but tagged as VERB',
                'confidence': 0.7
            }
        
        return None
    
    def detect_pron_det_confusion(self, item: LexicalItem, tree: SyntacticNode) -> Optional[Dict]:
        """
        PRON ↔ DET karışıklığı tespiti
        
        Hedef: Pro-drop + trace yapılarındaki hatalar
        
        Türkçe pro-drop:
        - "Ø geldi" (özne düşmüş, trace var)
        - "O geldi" (özne açık)
        
        Eğer trace varsa PRON, yoksa DET olabilir
        """
        # "o", "bu", "şu" gibi kelimeler
        if item.word.lower() not in ['o', 'bu', 'şu', 'bunlar', 'onlar', 'şunlar']:
            return None
        
        # Trace ile birlikte kullanılıyorsa PRON olmalı
        if tree and tree.trace:
            if item.pos == 'DET':
                return {
                    'type': POSErrorType.PRON_DET_CONFUSION,
                    'item': item,
                    'expected_pos': 'PRON',
                    'found_pos': 'DET',
                    'reason': 'Trace detected, should be PRON (pro-drop recovery)',
                    'confidence': 0.85
                }
        
        # İsimden önce geliyorsa DET olmalı
        # Context kontrolü gerekir (basitleştirilmiş)
        
        return None
    
    def detect_adj_noun_confusion(self, item: LexicalItem, context: List[LexicalItem]) -> Optional[Dict]:
        """
        ADJ ↔ NOUN karışıklığı tespiti
        
        Hedef: Adlaşmış sıfatlar
        
        Örnek:
        - "Güzel geldi" → "güzel" burada NOUN (adlaşmış)
        - "Güzel kız" → "güzel" burada ADJ
        """
        if item.word.lower() not in self.ADJECTIVAL_NOUNS:
            return None
        
        # Context'te başka isim yoksa adlaşmış olabilir
        has_following_noun = False
        try:
            item_index = context.index(item)
            if item_index < len(context) - 1:
                next_item = context[item_index + 1]
                if next_item.pos in ['NOUN', 'PROPN']:
                    has_following_noun = True
        except ValueError:
            pass
        
        # Sonrasında isim yoksa ama ADJ olarak etiketlenmişse
        if not has_following_noun and item.pos == 'ADJ':
            return {
                'type': POSErrorType.ADJ_NOUN_CONFUSION,
                'item': item,
                'expected_pos': 'NOUN',
                'found_pos': 'ADJ',
                'reason': 'Nominalized adjective (no following noun)',
                'confidence': 0.75
            }
        
        return None
    
    def detect_subject_object_mislabel(self, tree: SyntacticNode) -> List[Dict]:
        """
        SUBJECT ↔ OBJECT etiket hataları
        
        Hedef: Argüman yapısı uyumsuzlukları
        
        Minimalist teoride:
        - Fiil lexicon'dan argüman yapısıyla gelir (theta-grid)
        - "oku": [Agent, Theme] → SUBJ + OBJ gerektirir
        - Eğer sadece SUBJ varsa → HATA
        """
        errors = []
        
        # Basitleştirilmiş: Fiil düğümünü bul
        # Gerçek implementasyonda tree traversal gerekir
        
        return errors
    
    def phase_one_analysis(self, items: List[LexicalItem], tree: Optional[SyntacticNode] = None) -> List[Dict]:
        """
        AŞAMA 1: POS + Dependency → Aday hatalar
        
        Returns:
            Aday hata listesi
        """
        candidate_errors = []
        
        for item in items:
            # NOUN ↔ VERB kontrolü
            error = self.detect_noun_verb_confusion(item, items)
            if error:
                candidate_errors.append(error)
            
            # PRON ↔ DET kontrolü
            if tree:
                error = self.detect_pron_det_confusion(item, tree)
                if error:
                    candidate_errors.append(error)
            
            # ADJ ↔ NOUN kontrolü
            error = self.detect_adj_noun_confusion(item, items)
            if error:
                candidate_errors.append(error)
        
        # SUBJ ↔ OBJ kontrolü
        if tree:
            errors = self.detect_subject_object_mislabel(tree)
            candidate_errors.extend(errors)
        
        self.candidate_errors = candidate_errors
        return candidate_errors
    
    # ========== AŞAMA 2: Numeration + Movement Denetimi ==========
    
    def build_numeration(self, items: List[LexicalItem]) -> Numeration:
        """
        Lexical items'dan numeration oluştur
        
        Örnek:
        Input: [kitabı, okudu, Ali]
        Output: Numeration({kitabı:1, okudu:1, Ali:1})
        """
        item_counts = {}
        for item in items:
            item_counts[item] = item_counts.get(item, 0) + 1
        
        return Numeration(items=item_counts)
    
    def validate_selection_sequence(self, selection_history: SelectionHistory) -> List[Dict]:
        """
        SELECT operasyonlarının sırasını doğrula
        
        Minimalist kurallar:
        1. Fiil önce seçilmeli (theta-grid atar)
        2. Argümanlar theta-role sırasına göre (Agent > Theme > Goal)
        3. Fonksiyonel kategoriler son (T, C, D, vb.)
        
        Returns:
            Hata listesi
        """
        errors = []
        
        # Seçim sırası hatalarını kontrol et
        order_errors = selection_history.validate_selection_order()
        
        for error_msg in order_errors:
            errors.append({
                'type': POSErrorType.DISCOURSE_SYNTAX_CLASH,
                'reason': f'Selection order violation: {error_msg}',
                'confidence': 0.85
            })
        
        return errors
    
    def detect_movement_trace_mismatch(self, movements: List[Movement], tree: SyntacticNode) -> List[Dict]:
        """
        Movement ve trace uyumsuzluğu tespiti
        
        Hedef: "kitabı Ali okudu" gibi cümlelerde:
        - "kitabı" OBJECT'ten TOPIC'e hareket etmiş
        - Eski pozisyonda trace olmalı
        - Eğer trace yoksa veya POS yanlışsa → HATA
        """
        errors = []
        
        for movement in movements:
            if movement.requires_trace():
                # Trace varlığını kontrol et
                # Basitleştirilmiş: Tree'de trace aranır
                has_trace = self._find_trace_in_tree(tree, movement.trace_index)
                
                if not has_trace:
                    errors.append({
                        'type': POSErrorType.DISCOURSE_SYNTAX_CLASH,
                        'item': movement.element,
                        'reason': f'A-movement from {movement.from_position} requires trace',
                        'movement': movement,
                        'confidence': 0.95
                    })
        
        return errors
    
    def _find_trace_in_tree(self, tree: Optional[SyntacticNode], trace_index: int) -> bool:
        """Tree'de belirli index'li trace'i bul (recursive)"""
        if tree is None:
            return False
        
        if tree.trace and tree.trace.terminal:
            # Trace index kontrolü (basitleştirilmiş)
            return True
        
        # Recursive arama
        return (self._find_trace_in_tree(tree.head, trace_index) or
                self._find_trace_in_tree(tree.complement, trace_index) or
                self._find_trace_in_tree(tree.specifier, trace_index))
    
    def validate_numeration_consistency(self, num1: Numeration, num2: Numeration) -> bool:
        """
        İki numeration'ın tutarlılığını kontrol et
        
        Farklı türden numerationlar karşılaştırılamaz!
        
        Örnek:
        - "Ali geldi." vs "Ayşe Ali'nin geldiğini söyledi."
        - İkinci cümle embedded clause içeriyor → Farklı tür
        - Karşılaştırma yapılamaz → Olası hata
        """
        if not num1.compare_type(num2):
            return False
        return True
    
    def phase_two_analysis(self, 
                          numeration: Numeration,
                          movements: List[Movement],
                          tree: SyntacticNode,
                          alternative_numeration: Optional[Numeration] = None,
                          selection_history: Optional[SelectionHistory] = None) -> List[Dict]:
        """
        AŞAMA 2: Numeration + Movement + Selection → Gerçek hatalar
        
        Args:
            numeration: Ana numeration
            movements: Tespit edilen movement'lar
            tree: Sözdizim ağacı
            alternative_numeration: Alternatif parse'ın numeration'ı (karşılaştırma için)
            selection_history: SELECT operasyonları geçmişi (YENİ!)
        
        Returns:
            Doğrulanmış hata listesi
        """
        confirmed_errors = []
        
        # Movement-trace uyumsuzluğu
        movement_errors = self.detect_movement_trace_mismatch(movements, tree)
        confirmed_errors.extend(movement_errors)
        
        # Selection sequence doğrulama (YENİ!)
        if selection_history:
            selection_errors = selection_history.validate_selection_order()
            confirmed_errors.extend(selection_errors)
        elif numeration.selection_history.steps:
            # Numeration'ın kendi selection history'sini kullan
            selection_errors = numeration.selection_history.validate_selection_order()
            confirmed_errors.extend(selection_errors)
        
        # Alternatif numeration ile karşılaştırma
        if alternative_numeration:
            if not self.validate_numeration_consistency(numeration, alternative_numeration):
                # Farklı türden numerationlar → Yapısal tutarsızlık
                confirmed_errors.append({
                    'type': POSErrorType.DISCOURSE_SYNTAX_CLASH,
                    'reason': 'Numerations are of different types (incomparable derivations)',
                    'confidence': 0.8
                })
        
        self.confirmed_errors = confirmed_errors
        return confirmed_errors
    
    def detect_errors(self,
                     items: List[LexicalItem],
                     tree: Optional[SyntacticNode] = None,
                     movements: Optional[List[Movement]] = None,
                     alternative_items: Optional[List[LexicalItem]] = None,
                     selection_history: Optional[SelectionHistory] = None) -> Dict[str, Any]:
        """
        Tam hata tespiti pipeline'ı
        
        Args:
            items: Lexical items
            tree: Sözdizim ağacı (opsiyonel)
            movements: Movement listesi (opsiyonel)
            alternative_items: Alternatif parse'ın lexical items (opsiyonel)
            selection_history: SELECT operasyonları geçmişi (YENİ!)
        
        Returns:
            {
                'candidate_errors': [...],  # Aşama 1
                'confirmed_errors': [...],  # Aşama 2
                'selection_order': [...],   # SELECT sırası (YENİ!)
            }
        """
        # AŞAMA 1: POS + Dependency
        candidates = self.phase_one_analysis(items, tree)
        
        # AŞAMA 2: Numeration + Movement + Selection (opsiyonel)
        confirmed = []
        selection_order = []
        
        # Phase 2'yi çağır eğer movement VAR veya selection_history VAR ise
        if (movements and tree) or selection_history:
            numeration = self.build_numeration(items)
            alt_numeration = self.build_numeration(alternative_items) if alternative_items else None
            confirmed = self.phase_two_analysis(
                numeration, 
                movements if movements else [], 
                tree if tree else SyntacticNode(label="ROOT"), 
                alt_numeration,
                selection_history
            )
            
            # Selection order'ı kaydet
            if selection_history:
                selection_order = selection_history.get_selection_order()
            elif numeration.selection_history.steps:
                selection_order = numeration.selection_history.get_selection_order()
        
        return {
            'candidate_errors': candidates,
            'confirmed_errors': confirmed,
            'total_errors': len(candidates) + len(confirmed),
            'selection_order': selection_order
        }
    
    def get_error_report(self) -> str:
        """Hata raporu oluştur"""
        report = []
        report.append("=" * 60)
        report.append("MİNİMALİST PROGRAM - POS HATA TESPİTİ RAPORU")
        report.append("=" * 60)
        
        report.append(f"\n📊 AŞAMA 1: Aday Hatalar ({len(self.candidate_errors)})")
        for i, error in enumerate(self.candidate_errors, 1):
            report.append(f"\n{i}. {error['type'].value}")
            report.append(f"   Kelime: {error['item'].word}")
            report.append(f"   Bulunan: {error['found_pos']} → Beklenen: {error['expected_pos']}")
            report.append(f"   Sebep: {error['reason']}")
            report.append(f"   Güven: {error['confidence']:.0%}")
        
        report.append(f"\n\n🎯 AŞAMA 2: Doğrulanmış Hatalar ({len(self.confirmed_errors)})")
        for i, error in enumerate(self.confirmed_errors, 1):
            report.append(f"\n{i}. {error['type'].value}")
            if 'item' in error:
                report.append(f"   Kelime: {error['item'].word}")
            report.append(f"   Sebep: {error['reason']}")
            report.append(f"   Güven: {error['confidence']:.0%}")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)


# ========== EXPORT FONKSİYONLARI ==========

def create_lexical_item(word: str, pos: str, morphology: Optional[List[str]] = None, features: Optional[Dict] = None) -> LexicalItem:
    """
    LexicalItem oluşturmak için yardımcı fonksiyon
    
    Args:
        word: Kelime
        pos: POS etiketi
        morphology: Morfolojik özellikler listesi
        features: Özellikler dict
    
    Returns:
        LexicalItem (hashable)
    """
    morph_tuple = tuple(morphology) if morphology else tuple()
    feat_tuple = tuple(sorted(features.items())) if features else tuple()
    return LexicalItem(word, pos, morph_tuple, feat_tuple)


def export_for_centering_integration(detector: MinimalistPOSErrorDetector) -> Dict:
    """
    Merkezleme kuramı entegrasyonu için hata listesi export et
    
    Gelecekte centering_integration.py gibi bir dosyada:
    - Minimalist hatalar + Centering hatalar → Birleşik analiz
    """
    return {
        'minimalist_errors': detector.candidate_errors + detector.confirmed_errors,
        'error_types': [e['type'].value for e in detector.candidate_errors + detector.confirmed_errors],
        'high_confidence_errors': [
            e for e in detector.candidate_errors + detector.confirmed_errors 
            if e.get('confidence', 0) > 0.8
        ]
    }


# ========== DEMO ==========

def demo_minimalist_error_detection():
    """Minimalist POS hata tespiti demosu"""
    
    print("🔬 Minimalist Program - POS Hata Tespiti Demo\n")
    
    # Test case 1: NOUN ↔ VERB (nominal suffix)
    print("=" * 60)
    print("TEST 1: NOUN ↔ VERB Karışıklığı")
    print("Cümle: 'Ali'nin okuduğu kitap'")
    print("=" * 60)
    
    items1 = [
        create_lexical_item("Ali'nin", "PROPN"),
        create_lexical_item("okuduğu", "VERB", ["-DIK", "PAST"]),  # HATA! NOUN olmalı
        create_lexical_item("kitap", "NOUN")
    ]
    
    detector = MinimalistPOSErrorDetector()
    results = detector.detect_errors(items1)
    
    print(f"\n✅ Tespit edilen aday hatalar: {len(results['candidate_errors'])}")
    for error in results['candidate_errors']:
        print(f"  - {error['type'].value}: '{error['item'].word}' ({error['found_pos']} → {error['expected_pos']})")
    
    # Test case 2: Trace + Movement
    print("\n" + "=" * 60)
    print("TEST 2: Movement + Trace Kontrolü")
    print("Cümle: 'Kitabı Ali okudu' (OBJECT → TOPIC hareketi)")
    print("=" * 60)
    
    items2 = [
        create_lexical_item("kitabı", "NOUN", ["-i"], {'Case': 'ACC'}),
        create_lexical_item("Ali", "PROPN"),
        create_lexical_item("okudu", "VERB", ["PAST"], {'Tense': 'Past'})
    ]
    
    # Movement tanımlama
    movement = Movement(
        element=items2[0],  # "kitabı"
        from_position="OBJECT",
        to_position="TOPIC",
        trace_index=1
    )
    
    # Basit tree (trace olmadan - hata olmalı)
    tree = SyntacticNode(
        label="TP",
        head=SyntacticNode(label="VP", terminal=items2[2]),
        specifier=SyntacticNode(label="NP", terminal=items2[1])
    )
    
    detector2 = MinimalistPOSErrorDetector()
    results2 = detector2.detect_errors(items2, tree=tree, movements=[movement])
    
    print(f"\n✅ Doğrulanmış hatalar: {len(results2['confirmed_errors'])}")
    for error in results2['confirmed_errors']:
        print(f"  - {error['type'].value}: {error['reason']}")
    
    # Tam rapor
    print("\n" + "=" * 60)
    print("DETAYLI RAPOR")
    print("=" * 60)
    print(detector2.get_error_report())
    
    # Test case 3: Selection sequence
    print("\n" + "=" * 60)
    print("TEST 3: Selection Sequence Doğrulama")
    print("Cümle: 'Ali kitabı okudu'")
    print("=" * 60)
    
    items3 = [
        create_lexical_item("Ali", "PROPN"),
        create_lexical_item("kitabı", "NOUN", ["-i"]),
        create_lexical_item("okudu", "VERB", ["PAST"])
    ]
    
    # Doğru selection order: VERB → NOUN (Theme) → PROPN (Agent)
    from minimalist_pos_error_detection import SelectionHistory
    correct_selection = SelectionHistory()
    correct_selection.add_selection(items3[2], 1, 0)  # okudu (VERB) önce
    correct_selection.add_selection(items3[1], 2, 0)  # kitabı (Theme)
    correct_selection.add_selection(items3[0], 3, 0)  # Ali (Agent)
    
    # Yanlış selection order: PROPN önce (HATA!)
    wrong_selection = SelectionHistory()
    wrong_selection.add_selection(items3[0], 1, 0)  # Ali (PROPN) - YANLIŞ!
    wrong_selection.add_selection(items3[1], 2, 0)  # kitabı
    wrong_selection.add_selection(items3[2], 3, 0)  # okudu
    
    tree3 = SyntacticNode(label="TP")
    
    detector3_correct = MinimalistPOSErrorDetector()
    results3_correct = detector3_correct.detect_errors(
        items3, 
        tree=tree3, 
        movements=[],
        selection_history=correct_selection
    )
    
    detector3_wrong = MinimalistPOSErrorDetector()
    results3_wrong = detector3_wrong.detect_errors(
        items3,
        tree=tree3,
        movements=[],
        selection_history=wrong_selection
    )
    
    print(f"\n✅ DOĞRU Selection Sırası: {correct_selection.get_selection_order()}")
    print(f"   Hatalar: {len(results3_correct['confirmed_errors'])} (beklendiği gibi sıfır)")
    
    print(f"\n❌ YANLIŞ Selection Sırası: {wrong_selection.get_selection_order()}")
    print(f"   Hatalar: {len(results3_wrong['confirmed_errors'])}")
    for error in results3_wrong['confirmed_errors']:
        print(f"   - {error['reason']}")


if __name__ == "__main__":
    demo_minimalist_error_detection()
