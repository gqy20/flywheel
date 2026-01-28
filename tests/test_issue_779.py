"""Test for Issue #779 - Inconsistent Unicode normalization strategy.

This test verifies that fullwidth characters are converted to their ASCII
equivalents using NFKC normalization rather than being deleted.

The issue: Code uses NFC normalization to preserve semantic meaning,
but then deletes fullwidth characters with regex r'[\uFF01-\uFF60]'.
If fullwidth inputs are considered 'spoofing' and must be removed,
NFKC normalization would be more appropriate as it converts fullwidth
characters to their ASCII equivalents (e.g., 'Ａ' to 'A'), preserving
data rather than deleting it.
"""

import pytest
from flywheel.cli import sanitize_string


class TestFullwidthCharacterHandling:
    """Test that fullwidth characters are converted (not deleted)."""

    def test_fullwidth_letters_converted_to_ascii(self):
        """Fullwidth Latin letters should be converted to ASCII equivalents."""
        # Fullwidth ＡＢＣ should become ABC
        result = sanitize_string("ＡＢＣ")
        assert result == "ABC", f"Expected 'ABC' but got '{result}'"

    def test_fullwidth_digits_converted_to_ascii(self):
        """Fullwidth digits should be converted to ASCII equivalents."""
        # Fullwidth ０１２３ should become 0123
        result = sanitize_string("０１２３")
        assert result == "0123", f"Expected '0123' but got '{result}'"

    def test_fullwidth_punctuation_converted_to_ascii(self):
        """Fullwidth punctuation should be converted to ASCII equivalents."""
        # Fullwidth ！＂＃ should become !"# (but " is removed by sanitize_string)
        result = sanitize_string("！＂＃")
        # After sanitization, quotes may be removed, but ! and # should remain
        assert "!" in result or "#" in result, f"Expected ! or # but got '{result}'"

    def test_mixed_fullwidth_and_regular_text(self):
        """Mixed fullwidth and regular text should be handled properly."""
        # "HelloＷorld" should become "HelloWorld" or "Hello World"
        result = sanitize_string("HelloＷorld")
        # The fullwidth W should be converted to regular W
        assert "W" in result, f"Expected 'W' in result but got '{result}'"
        assert "Ｗ" not in result, "Fullwidth W should be converted"

    def test_fullwidth_exclamation_mark(self):
        """Fullwidth exclamation mark should be converted."""
        result = sanitize_string("Ｈｅｌｌｏ！")
        # Fullwidth ！ (U+FF01) should be converted to ! (U+0021)
        assert "!" in result, f"Expected '!' in result but got '{result}'"
        assert "Hello" in result or "hello" in result, f"Expected 'Hello' but got '{result}'"

    def test_fullwidth_parentheses_converted(self):
        """Fullwidth parentheses should be converted if preserved."""
        # Note: sanitize_string removes all parentheses
        # So we test that the text around them is preserved
        result = sanitize_string("test（value）")
        # Fullwidth parentheses should be removed like regular ones
        # but the text should remain
        assert "test" in result and "value" in result, f"Expected 'test' and 'value' but got '{result}'"
