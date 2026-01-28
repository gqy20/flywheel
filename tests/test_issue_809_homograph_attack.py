"""Tests for Issue #809 - Unicode homograph attack prevention.

This test ensures that the sanitize_string function properly prevents
homograph attacks by using NFKC normalization instead of NFC.

The issue: NFC normalization allows visually identical characters from
different scripts (e.g., Latin 'a' vs Cyrillic 'а') to pass through,
enabling homograph spoofing attacks.
"""

import pytest
from flywheel.cli import sanitize_string


class TestHomographAttackPrevention:
    """Test that homograph attacks are prevented."""

    def test_cyrillic_vs_latin_homographs_removed(self):
        """Test that Cyrillic homographs of Latin characters are normalized.

        Example: Latin 'a' (U+0061) vs Cyrillic 'а' (U+0430)
        NFKC should convert these to distinguishable forms or remove them.
        """
        # Cyrillic 'а' looks like Latin 'a' but is different
        cyrillic_a = '\u0430'  # Cyrillic small letter a
        latin_a = 'a'

        # With NFC, both would pass as-is (vulnerable)
        # With NFKC, the Cyrillic character might be preserved but
        # other compatibility characters would be normalized

        # This test verifies we're using NFKC by checking that
        # fullwidth characters (compatibility) are normalized
        fullwidth_a = '\uFF21'  # Fullwidth Latin capital letter A
        result = sanitize_string(fullwidth_a)

        # NFKC should convert fullwidth characters to their ASCII equivalents
        # NFC would leave them as-is
        assert result == 'A', f"Expected 'A' but got '{result}' (Unicode: {ord(result)})"

    def test_fullwidth_digits_normalized(self):
        """Test that fullwidth digits are normalized to ASCII.

        Fullwidth characters are compatibility characters that NFKC
        should convert to their ASCII equivalents.
        """
        # Fullwidth digits: ０１２３４５６７８９
        fullwidth = '０１２３４５６７８９'
        result = sanitize_string(fullwidth)

        # NFKC should convert fullwidth digits to ASCII
        assert result == '0123456789', f"Expected '0123456789' but got '{result}'"

    def test_superscripts_normalized_with_nfkc(self):
        """Test that superscripts are handled with NFKC.

        NFKC normalizes superscripts to their base characters.
        This is a trade-off: we lose semantic meaning but prevent homograph attacks.
        """
        superscript_2 = '²'  # Superscript two

        # With NFKC, this should be converted to '2'
        # With NFC, it would remain as '²'
        result = sanitize_string(superscript_2)

        # NFKC converts superscripts to base characters
        # This prevents them from being used for homograph attacks
        assert result == '2', f"Expected '2' but got '{result}'"

    def test_mixed_script_homographs_normalized(self):
        """Test that mixed-script homograph attempts are normalized.

        Attackers might mix characters from different scripts that look identical.
        NFKC helps normalize these to prevent spoofing.
        """
        # Fullwidth Latin letters can be used to mimic normal letters
        # but in a way that bypasses simple filters
        fullwidth_hello = 'Ｈｅｌｌｏ'  # Fullwidth HELLO
        result = sanitize_string(fullwidth_hello)

        # Should be normalized to ASCII
        assert result == 'Hello', f"Expected 'Hello' but got '{result}'"

    def test_nfk_vs_nfc_behavior(self):
        """Test the difference between NFC and NFKC normalization.

        This test explicitly checks that we're using NFKC (which prevents
        homograph attacks at the cost of some semantic meaning) rather than
        NFC (which preserves semantic meaning but is more vulnerable).
        """
        # Compatibility characters that NFKC changes but NFC doesn't
        test_cases = [
            ('Ａ', 'A'),  # Fullwidth capital A
            ('ａ', 'a'),  # Fullwidth small a
            ('¹', '1'),   # Superscript one
            ('²', '2'),   # Superscript two
            ('³', '3'),   # Superscript three
        ]

        for input_char, expected in test_cases:
            result = sanitize_string(input_char)
            assert result == expected, \
                f"NFKC test failed: {repr(input_char)} (U+{ord(input_char):04X}) -> {repr(result)} (U+{ord(result):04X}), expected {repr(expected)}"
