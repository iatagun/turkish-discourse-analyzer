"""
Türkçe POS Tagging Tercih Tespiti - Basit Python API
==================================================

Kullanım:
    from api.main import check_sentence, detect_minimalist_errors
    
    # Basit kontrol
    result = check_sentence("Ali'nin okuduğu kitap burada.")
    
    # Minimalist analiz
    errors = detect_minimalist_errors(words)
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Parent directories'i path'e ekle
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from error_detection.minimalist_pos_error_detection import (  # type: ignore
    MinimalistPOSErrorDetector,
    create_lexical_item
)

# Stanza lazy import (sadece ihtiyaç olursa yükle)
_stanza_pipeline = None

def _get_stanza_pipeline():
    """Stanza pipeline'ı lazy load et"""
    global _stanza_pipeline
    if _stanza_pipeline is None:
        try:
            import stanza
            _stanza_pipeline = stanza.Pipeline('tr', processors='tokenize,pos,lemma,depparse', verbose=False)
        except ImportError:
            raise ImportError("Stanza kurulu değil. Yüklemek için: pip install stanza")
        except Exception:
            # Model yoksa indir
            import stanza
            stanza.download('tr')
            _stanza_pipeline = stanza.Pipeline('tr', processors='tokenize,pos,lemma,depparse', verbose=False)
    return _stanza_pipeline


def extract_morphology_from_text(text: str) -> List[str]:
    """
    Kelime sonuna bakarak nominal ekleri çıkar
    
    Parser'lar morfoloji vermez, bu yüzden kural tabanlı çıkarım yapıyoruz.
    """
    morphology = []
    text_lower = text.lower()
    
    # -DIK eki (duğu, dığı, tuğu, tığı, dük, dik, tuk, tik)
    if any(text_lower.endswith(suffix) for suffix in 
           ['duğu', 'dığı', 'tuğu', 'tığı', 'duğum', 'dığım', 'duğun', 'dığın']):
        morphology.append('-DIK')
    
    # -mA eki (ma, me ile biten ve sonrasında iyelik/belirtme gelmemiş)
    if text_lower.endswith(('ma', 'me')) and len(text) > 2:
        morphology.append('-mA')
    
    # -Iş eki (ış, iş, uş, üş)
    if any(text_lower.endswith(suffix) for suffix in ['ış', 'iş', 'uş', 'üş']):
        morphology.append('-Iş')
    
    # -mAk eki (mak, mek)
    if any(text_lower.endswith(suffix) for suffix in ['mak', 'mek']):
        morphology.append('-mAk')
    
    return morphology


def is_finite_verb(feats: str) -> bool:
    """
    FEATS bilgisine bakarak finit fiil olup olmadığını kontrol et
    
    TEORİK TEMEL (Önermesel Semantik - Yüklem Tipi):
    
    PARÇALI YÜKLEM (Finite - zamana gönderimli):
    - Tense (zaman): Past, Pres, Fut → Zamanda bir noktaya oturur
    - Mood (kip): Ind, Imp, Opt → Bildirim değeri var
    - Aspect (görünüş): Perf, Imp, Prog → Olay tümcesi
    - Örnek: "Kuşlar uçtu" (parçalı, sentetik önerme)
    
    BÜTÜNCÜL YÜKLEM (Non-finite - generic):
    - VerbForm=Vnoun, VerbForm=Part → Nominal domain
    - Tense=Aor (geniş zaman) → Özellik tümcesi
    - Örnek: "Kuşlar uçar" (bütüncül, analitik önerme)
    
    NON-finite (nominal) özellikleri:
    - Case (durum eki): Nom, Acc, Dat, Loc, Abl, Gen
    - Person[psor] (iyelik): iyelik eki varsa nominal
    
    Args:
        feats: Stanza feats string (ör: "Case=Nom|Number=Sing|Person=3|Tense=Past")
        
    Returns:
        True ise finit fiil (normal fiil), False ise nominal/non-finite
    """
    if not feats:
        return False
    
    feats_lower = feats.lower()
    
    # İyelik eki varsa nominal (-DIK+iyelik gibi)
    if 'person[psor]' in feats_lower:
        return False
    
    # Durum eki varsa nominal
    if 'case=' in feats_lower and 'case=nom' not in feats_lower:
        return False
    
    # Zaman eki varsa finit fiil
    if any(tense in feats_lower for tense in ['tense=past', 'tense=pres', 'tense=fut']):
        return True
    
    # Kip eki varsa finit fiil
    if any(mood in feats_lower for mood in ['mood=ind', 'mood=imp', 'mood=opt']):
        return True
    
    # Aspect varsa finit fiil
    if any(aspect in feats_lower for aspect in ['aspect=perf', 'aspect=imp', 'aspect=prog']):
        return True
    
    # VerbForm=Fin varsa kesin finit
    if 'verbform=fin' in feats_lower:
        return True
    
    return False


def format_error_type_academic(error_type: str, found_pos: str, expected_pos: str) -> str:
    """
    Hata tipini akademik formata çevir
    
    NOT: "Hata" terimi UD açısından yanlıştır. Bu tespitler:
    - UD standardına uygun etiketlerin discourse/semantic görevler için yetersiz kalması
    - Nominal domain preference (adlaşma eğilimi) göstergeleri
    - Task-driven relabeling önerileri
    
    Args:
        error_type: POSErrorType enum değeri (ör: "NOUN ↔ VERB")
        found_pos: Bulunan UD etiketi
        expected_pos: Görev için önerilen etiket
        
    Returns:
        Akademik format (ör: "Nominal domain preference (VERB-origin)")
    """
    # NOUN ↔ VERB: Nominal domain preference
    if "NOUN" in error_type and "VERB" in error_type:
        if found_pos == "VERB" and expected_pos == "NOUN":
            return "Nominal domain preference (VERB-origin)"
        elif found_pos == "NOUN" and expected_pos == "VERB":
            return "Verbal domain preference (NOUN-origin)"
    
    # ADJ ↔ NOUN: Nominal domain preference
    elif "ADJ" in error_type and "NOUN" in error_type:
        if found_pos == "ADJ" and expected_pos == "NOUN":
            return "Nominal domain preference (ADJ-origin)"
        elif found_pos == "NOUN" and expected_pos == "ADJ":
            return "Adjectival domain preference (NOUN-origin)"
    
    # PRON ↔ DET: Discourse-driven relabeling
    elif "PRON" in error_type and "DET" in error_type:
        return "Discourse-driven relabeling (DET→PRON for coreference)"
    
    # SUBJ ↔ OBJ: Argument structure
    elif "SUBJ" in error_type and "OBJ" in error_type:
        return "Argument structure inconsistency"
    
    # Diğerleri için orijinal format
    return error_type


def detect_minimalist_errors(words: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Minimalist Program ile POS hata tespiti
    
    Args:
        words: Kelime listesi (parser çıktısı)
        # FEATS bilgisi - finit fiil kontrolü için
        feats = word.get("feats", "")
        
        # Finit fiil ise ve nominal ek yoksa, features dict oluştur
        features = {}
        if is_finite_verb(feats):
            features["FINITE_VERB"] = True
        
        lex_item = create_lexical_item(
            word=word["text"],
            pos=word["pos"],
            morphology=morphology,
            features=features  # Dict olarak gönder
        {
            "total_errors": int,
            "errors": [
                {
                    "word": str,
                    "type": str,
                    "found_pos": str,
                    "expected_pos": str,
                    "reason": str,
                    "confidence": float
                }
            ]
        }
    
    Örnek:
        >>> words = [
        ...     {"text": "okuduğu", "pos": "VERB"},  # Parser çıktısı
        ...     {"text": "kitap", "pos": "NOUN"}
        ... ]
        >>> result = detect_minimalist_errors(words)
        >>> print(result["total_errors"])
        1
    """
    detector = MinimalistPOSErrorDetector()
    
    # LexicalItem'lar oluştur
    lex_items = []
    for word in words:
        # Morfolojiyi kelime sonundan çıkar (parser vermez!)
        morphology = word.get("morphology", extract_morphology_from_text(word["text"]))
        
        # FEATS bilgisi - finit fiil kontrolü için
        feats = word.get("feats", "")
        
        # Finit fiil ise ve nominal ek yoksa, features dict oluştur
        features = {}
        if is_finite_verb(feats):
            features["FINITE_VERB"] = True
        
        lex_item = create_lexical_item(
            word=word["text"],
            pos=word["pos"],
            morphology=morphology,
            features=features
        )
        lex_items.append(lex_item)
    
    # Hata tespiti
    results = detector.detect_errors(lex_items)
    
    # Basit formata dönüştür
    errors = []
    for err in results.get('candidate_errors', []):
        academic_type = format_error_type_academic(
            err['type'].value, 
            err['found_pos'], 
            err['expected_pos']
        )
        errors.append({
            "word": err['item'].word,
            "type": academic_type,
            "found_pos": err['found_pos'],
            "expected_pos": err['expected_pos'],
            "reason": err['reason'],
            "confidence": err['confidence']
        })
    
    for err in results.get('confirmed_errors', []):
        # Confirmed errors için de akademik format
        err_type = err.get('type', 'UNKNOWN')
        if hasattr(err_type, 'value'):
            academic_type = format_error_type_academic(
                err_type.value,
                "N/A",
                "N/A"
            )
        else:
            academic_type = str(err_type)
            
        errors.append({
            "word": err.get('item', {}).word if 'item' in err else "N/A",
            "type": academic_type,
            "found_pos": "N/A",
            "expected_pos": "N/A",
            "reason": err.get('reason', 'Unknown'),
            "confidence": err.get('confidence', 0.0)
        })
    
    return {
        "total_errors": len(errors),
        "errors": errors
    }


def check_sentence(text: str) -> Dict[str, Any]:
    """
    TEK SATIRDA POS HATA TESPİTİ
    
    Cümleyi otomatik parse edip hataları döner.
    
    Args:
        text: Türkçe cümle
        
    Returns:
        {
            "sentence": str,
            "words": [{"text": str, "pos": str, "lemma": str}],
            "errors": [{...}],
            "total_errors": int
        }
        
    Örnek:
        >>> from api.main import check_sentence
        >>> result = check_sentence("Ali'nin okuduğu kitap")
        >>> print(f"{result['total_errors']} hata bulundu")
        1 hata bulundu
    """
    nlp = _get_stanza_pipeline()
    doc = nlp(text)
    
    # Parse edilmiş kelimeleri çıkar (FEATS dahil!)
    words = []
    for sent in getattr(doc, 'sentences', []):
        for word in sent.words:
            words.append({
                "text": word.text,
                "pos": word.upos,
                "lemma": word.lemma,
                "dependency": word.deprel,
                "feats": word.feats if word.feats else ""  # FEATS eklendi!
            })
    
    # Hata tespiti
    result = detect_minimalist_errors(words)
    
    return {
        "sentence": text,
        "words": words,
        "errors": result["errors"],
        "total_errors": result["total_errors"]
    }
