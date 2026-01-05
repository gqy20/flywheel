"""Test for issue #764 - NFKC normalization data loss

This test verifies that the sanitize_string function preserves
semantic meaning of characters while still normalizing Unicode.
NFKC normalization causes data loss for characters like:
- Superscript digits (², ³) which become regular digits (2, 3)
- Ligatures (ﬁ, ﬂ) which become decomposed (fi, fl)
- Other compatibility characters that lose their semantic meaning
"""

import pytest
from flywheel.cli import sanitize_string


def test_superscript_two_preserved():
    """Test that superscript ² character is preserved."""
    # Superscript TWO (U+00B2) should be preserved
    # With NFKC: becomes '2' (data loss)
    # With NFC: remains '²' (preserved)
    input_str = "x²"
    result = sanitize_string(input_str)
    # NFC preserves the superscript
    assert result == "x²", f"Expected 'x²' but got '{result}'"


def test_ligature_fi_preserved():
    """Test that ligature ﬁ character is preserved."""
    # LATIN SMALL LIGATURE FI (U+FB01) should be preserved
    # With NFKC: becomes 'fi' (data loss)
    # With NFC: remains 'ﬁ' (preserved)
    input_str = "ﬁ"
    result = sanitize_string(input_str)
    # NFC preserves the ligature
    assert result == "ﬁ", f"Expected 'ﬁ' but got '{result}'"


def test_composed_e_acute_normalized():
    """Test that composed é is properly normalized (NFC)."""
    # When using NFC, é (U+00E9) and e + combining acute (U+0065 U+0301)
    # should both normalize to the composed form é (U+00E9)
    # This tests that NFC is working correctly
    input_composed = "é"  # U+00E9 - LATIN SMALL LETTER E WITH ACUTE
    input_decomposed = "e\u0301"  # e + combining acute accent

    result_composed = sanitize_string(input_composed)
    result_decomposed = sanitize_string(input_decomposed)

    # NFC normalizes both to the same composed form
    assert result_composed == "é"
    assert result_decomposed == "é"
    assert result_composed == result_decomposed


def test_mixed_superscript_text():
    """Test that mixed text with superscripts is preserved."""
    input_str = "The formula is E=mc² and x³ + y³ = z³"
    result = sanitize_string(input_str)
    # NFC should preserve all superscript characters
    assert "²" in result, f"Superscript ² should be preserved, got: {result}"
    assert "³" in result, f"Superscript ³ should be preserved, got: {result}"


def test_ordinals_preserved():
    """Test that ordinal characters like ª and º are preserved."""
    # FEMININE ORDINAL INDICATOR (U+00AA) and MASCULINE ORDINAL INDICATOR (U+00BA)
    # With NFKC: become 'a' and 'o' (data loss)
    # With NFC: remain 'ª' and 'º' (preserved)
    input_str = "1ª 2º"
    result = sanitize_string(input_str)
    assert result == "1ª 2º", f"Expected '1ª 2º' but got '{result}'"
