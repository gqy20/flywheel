#!/usr/bin/env python
"""Demo script showing NFKC causes data loss."""

import unicodedata

# Current implementation uses NFKC
def current_sanitize(s: str) -> str:
    s = unicodedata.normalize('NFKC', s)
    return s

# Proposed fix uses NFC
def proposed_sanitize(s: str) -> str:
    s = unicodedata.normalize('NFC', s)
    return s

# Test cases showing data loss
test_cases = [
    ("x²", "Superscript TWO (U+00B2)"),
    ("ﬁ", "Ligature FI (U+FB01)"),
    ("1ª 2º", "Ordinal indicators"),
]

print("=" * 60)
print("RED Phase: Demonstrating NFKC causes data loss")
print("=" * 60)

for input_str, description in test_cases:
    current_result = current_sanitize(input_str)
    proposed_result = proposed_sanitize(input_str)

    print(f"\n{description}:")
    print(f"  Input:   '{input_str}' (U+{ord(input_str[0] if input_str[0] != ' ' else input_str[1]):04X})")
    print(f"  NFKC:    '{current_result}' {'❌ DATA LOSS' if current_result != input_str else '✓'}")
    print(f"  NFC:     '{proposed_result}' {'✓ PRESERVED' if proposed_result == input_str else '❌'}")

print("\n" + "=" * 60)
print("Conclusion: NFKC causes data loss, NFC preserves meaning")
print("=" * 60)
