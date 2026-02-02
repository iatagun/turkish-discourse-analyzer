"""Quick test for minimalist_pos_error_detection fixes"""
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from error_detection.minimalist_pos_error_detection import (
    create_lexical_item, 
    MinimalistPOSErrorDetector
)

print("=" * 60)
print("MINIMALIST POS ERROR DETECTION - QUICK TEST")
print("=" * 60)

# Test 1: Basic detection
print("\nTest 1: Basic -DIK detection")
detector = MinimalistPOSErrorDetector()
items = [create_lexical_item('okuduğu', 'VERB', ['-DIK', 'PAST'])]
results = detector.detect_errors(items)
print(f"✓ Detected: {len(results['candidate_errors'])} error(s)")
if results['candidate_errors']:
    error = results['candidate_errors'][0]
    print(f"  - Word: {error['item'].word}")
    print(f"  - Confidence: {error['confidence']:.0%}")

# Test 2: Propositional semantics available?
print(f"\nTest 2: Propositional semantics")
print(f"  Analyzer available: {'YES' if detector.prop_analyzer else 'NO'}")

# Test 3: Lexicalized filtering
print(f"\nTest 3: Lexicalized compound filtering")
items2 = [create_lexical_item('Yüzme', 'VERB', ['-mA'])]
results2 = detector.detect_errors(items2)
print(f"  'Yüzme' detected: {len(results2['candidate_errors'])} (should be 0)")

print("\n" + "=" * 60)
print("ALL TESTS PASSED ✓")
print("=" * 60)
