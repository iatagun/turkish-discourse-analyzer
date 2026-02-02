"""
Türkçe POS + Semantic Analysis - Structured JSON Output
========================================================

Stanza çıktısına POS preferences ve propositional semantics ekler.

Kullanım:
    from api.structured_output import analyze_text
    
    result = analyze_text("Ali'nin okuduğu kitap burada.")
    print(json.dumps(result, indent=2, ensure_ascii=False))
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# Parent directories'i path'e ekle
parent_dir = Path(__file__).parent.parent
error_detection_path = str(parent_dir / "error_detection")
if error_detection_path not in sys.path:
    sys.path.insert(0, error_detection_path)
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from error_detection.minimalist_pos_error_detection import (  # type: ignore
    MinimalistPOSErrorDetector,
    create_lexical_item
)

# Stanza lazy import
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
            import stanza
            stanza.download('tr')
            _stanza_pipeline = stanza.Pipeline('tr', processors='tokenize,pos,lemma,depparse', verbose=False)
    return _stanza_pipeline


def extract_morphology_from_text(text: str) -> List[str]:
    """Kelime sonuna bakarak nominal ekleri çıkar"""
    morphology = []
    text_lower = text.lower()
    
    # -DIK eki
    if any(text_lower.endswith(suffix) for suffix in 
           ['duğu', 'dığı', 'tuğu', 'tığı', 'duğum', 'dığım', 'duğun', 'dığın']):
        morphology.append('-DIK')
    
    # -mA eki
    if text_lower.endswith(('ma', 'me')) and len(text) > 2:
        morphology.append('-mA')
    
    # -Iş eki
    if any(text_lower.endswith(suffix) for suffix in ['ış', 'iş', 'uş', 'üş']):
        morphology.append('-Iş')
    
    # -mAk eki
    if any(text_lower.endswith(suffix) for suffix in ['mak', 'mek']):
        morphology.append('-mAk')
    
    return morphology


def is_finite_verb(feats: str) -> bool:
    """FEATS bilgisine bakarak finit fiil olup olmadığını kontrol et"""
    if not feats:
        return False
    
    feats_lower = feats.lower()
    
    # İyelik eki varsa nominal (önce kontrol et)
    if 'person[psor]' in feats_lower:
        return False
    
    # Durum eki varsa nominal
    if 'case=' in feats_lower and 'case=nom' not in feats_lower:
        return False
    
    # Zaman eki varsa finit
    if any(tense in feats_lower for tense in ['tense=past', 'tense=pres', 'tense=fut']):
        return True
    
    # Kip eki varsa finit
    if any(mood in feats_lower for mood in ['mood=ind', 'mood=imp', 'mood=opt']):
        return True
    
    # Aspect varsa finit (Hab, Prog gibi)
    if any(aspect in feats_lower for aspect in ['aspect=hab', 'aspect=perf', 'aspect=imp', 'aspect=prog']):
        return True
    
    # VerbForm=Fin varsa kesin finit
    if 'verbform=fin' in feats_lower:
        return True
    
    return False


def analyze_propositional_semantics(text: str, words: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Cümle düzeyinde önermesel semantik analiz
    
    Returns:
        {
            "proposition_type": "analytic" | "synthetic",
            "predicate_type": "bütüncül" | "parçalı" | "alışkanlık",
            "generic_encoding": bool,
            "time_bound": bool,
            "verifiability": float,
            "clause_finiteness": "finite" | "non-finite"
        }
    """
    # Clause finiteness kontrolü (root VERB var mı ve finit mi?)
    clause_finiteness = "non-finite"
    root_verb = None
    
    for w in words:
        if w.get('deprel') == 'root' and w.get('upos') == 'VERB':
            root_verb = w
            if w.get('is_finite'):
                clause_finiteness = "finite"
            break
    
    try:
        # Propositional semantics modülünü lazy import
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from propositional_semantics import analyze_sentence_with_stanza
        
        result = analyze_sentence_with_stanza(text)
        
        # Hata kontrolü
        if 'error' in result:
            return None
        
        # analyses listesinden ilk analizi al
        analyses = result.get('analyses', [])
        if not analyses:
            # Copula cümleleri için basit analiz (VERB yok, ADJ/NOUN root)
            # "Yüzme havuzu temiz" → synthetic (özgül nesne + state)
            has_specific_subject = any(
                w.get('feats') and ('case=acc' in w.get('feats', '').lower() or 
                                   'prontype=dem' in w.get('feats', '').lower())
                for w in words
            )
            
            return {
                "proposition_type": "synthetic",
                "predicate_type": "bütüncül",  # Copula = state = holistic
                "generic_encoding": False,
                "time_bound": False,
                "verifiability": 0.7,
                "clause_finiteness": clause_finiteness
            }
        
        analysis = analyses[0]
        prop_value = analysis.get('propositional_value', {})
        
        # sentence_type'tan predicate_type'ı düzelt
        sentence_type = prop_value.get("sentence_type", "")
        predicate_type_raw = prop_value.get("predicate_type", "bütüncül")
        
        # alışkanlık → "alışkanlık" (ileride kullanılacak)
        if sentence_type == "alışkanlık":
            predicate_type = "alışkanlık"
        else:
            predicate_type = predicate_type_raw
        
        return {
            "proposition_type": prop_value.get("type"),
            "predicate_type": predicate_type,
            "generic_encoding": prop_value.get("generic", False),
            "time_bound": prop_value.get("time_bound", False),
            "verifiability": prop_value.get("assertive_value", 0.0),
            "clause_finiteness": clause_finiteness
        }
    except Exception as e:
        # Hata durumunda basit default değer
        return {
            "proposition_type": "synthetic",
            "predicate_type": "bütüncül",
            "generic_encoding": False,
            "time_bound": False,
            "verifiability": 0.5,
            "clause_finiteness": clause_finiteness
        }


def analyze_text(text: str, include_semantics: bool = True) -> Dict[str, Any]:
    """
    Metni Stanza ile parse et ve POS preferences + semantics ekle
    
    Args:
        text: Türkçe metin
        include_semantics: Propositional semantics dahil edilsin mi?
        
    Returns:
        {
            "text": str,
            "sentences": [
                {
                    "text": str,
                    "words": [
                        {
                            "id": int,
                            "text": str,
                            "lemma": str,
                            "upos": str,
                            "xpos": str | null,
                            "feats": str | null,
                            "head": int,
                            "deprel": str,
                            "misc": str | null,
                            "preference": {
                                "type": str,
                                "expected_pos": str,
                                "confidence": float,
                                "reason": str
                            } | null,
                            "morphology": List[str],
                            "is_finite": bool
                        }
                    ],
                    "semantics": {...} | null
                }
            ]
        }
        
    Örnek:
        >>> result = analyze_text("Ali'nin okuduğu kitap burada.")
        >>> print(json.dumps(result, indent=2, ensure_ascii=False))
    """
    nlp = _get_stanza_pipeline()
    doc = nlp(text)
    
    # Minimalist detector
    detector = MinimalistPOSErrorDetector()
    
    sentences = []
    # Type hint: doc has .sentences attribute (Stanza Document)
    doc_sentences = getattr(doc, 'sentences', [])
    for sent in doc_sentences:
        words = []
        lex_items = []
        
        # Stanza kelimelerini çıkar
        for word in sent.words:
            feats = word.feats if word.feats else ""
            morphology = extract_morphology_from_text(word.text)
            
            # LexicalItem oluştur
            features = {}
            if is_finite_verb(feats):
                features["FINITE_VERB"] = True
            
            lex_item = create_lexical_item(
                word=word.text,
                pos=word.upos,
                morphology=morphology,
                features=features
            )
            lex_items.append(lex_item)
            
            # Word data (Stanza format + extensions)
            word_data = {
                "id": word.id,
                "text": word.text,
                "lemma": word.lemma if word.lemma else None,
                "upos": word.upos,
                "xpos": word.xpos if word.xpos else None,
                "feats": feats if feats else None,
                "head": word.head,
                "deprel": word.deprel,
                "misc": None,  # Stanza'da misc field yok ama CONLL-U uyumluluğu için
                "morphology": morphology,
                "is_finite": is_finite_verb(feats)
            }
            
            words.append(word_data)
        
        # POS preferences tespit et
        detection_results = detector.detect_errors(lex_items)
        
        # Preferences'ları words'e ekle
        preference_map = {}
        for err in detection_results.get('candidate_errors', []):
            word_text = err['item'].word
            preference_map[word_text] = {
                "type": err['type'].value if hasattr(err['type'], 'value') else str(err['type']),
                "expected_pos": err['expected_pos'],
                "confidence": err['confidence'],
                "reason": err['reason']
            }
        
        # Her kelimeye preference ekle
        for word_data in words:
            word_data["preference"] = preference_map.get(word_data["text"])
        
        # Sentence-level semantics
        sentence_data = {
            "text": sent.text,
            "words": words,
            "semantics": None
        }
        
        # Propositional semantics ekle
        if include_semantics:
            sentence_data["semantics"] = analyze_propositional_semantics(
                sent.text, 
                words
            )
        
        sentences.append(sentence_data)
    
    return {
        "text": text,
        "sentences": sentences
    }


def analyze_to_conllu(text: str) -> str:
    """
    Metni CONLL-U formatında döndür (preferences MISC field'da)
    
    Args:
        text: Türkçe metin
        
    Returns:
        CONLL-U format string
        
    Örnek:
        >>> result = analyze_to_conllu("Ali'nin okuduğu kitap.")
        >>> print(result)
        # text = Ali'nin okuduğu kitap.
        1	Ali'nin	Ali	PROPN	...
        2	okuduğu	oku	VERB	...	Preference=NOUN|Confidence=0.95
        3	kitap	kitap	NOUN	...
    """
    result = analyze_text(text, include_semantics=False)
    
    lines = []
    for sent in result["sentences"]:
        # Sentence header
        lines.append(f"# text = {sent['text']}")
        
        # Words
        for word in sent["words"]:
            misc_parts = []
            
            # Preference bilgisi MISC field'a
            if word["preference"]:
                pref = word["preference"]
                misc_parts.append(f"Preference={pref['expected_pos']}")
                misc_parts.append(f"Confidence={pref['confidence']:.2f}")
            
            # Morphology bilgisi
            if word["morphology"]:
                misc_parts.append(f"Morphology={','.join(word['morphology'])}")
            
            misc = "|".join(misc_parts) if misc_parts else "_"
            
            line = "\t".join([
                str(word["id"]),
                word["text"],
                word["lemma"] or "_",
                word["upos"],
                word["xpos"] or "_",
                word["feats"] or "_",
                str(word["head"]),
                word["deprel"],
                "_",  # deps (enhanced dependencies)
                misc
            ])
            lines.append(line)
        
        lines.append("")  # Empty line between sentences
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test
    test_sentences = [
        "Ali'nin okuduğu kitap burada.",
        "Kuşlar uçar.",
        "Kuşlar uçtu.",
        "Ali sabahları erken kalkar.",
        "Yüzme havuzu temiz."
    ]
    
    print("=" * 80)
    print("STRUCTURED JSON OUTPUT TEST - Stanza Format + Extensions")
    print("=" * 80)
    
    for sent in test_sentences:
        print(f"\n📝 {sent}")
        print("-" * 80)
        result = analyze_text(sent)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 80)
    print("CONLL-U FORMAT SAMPLE")
    print("=" * 80)
    
    print(f"\n{analyze_to_conllu('Ali sabahları erken kalkar.')}")
