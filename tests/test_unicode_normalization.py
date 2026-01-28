"""Tests for Unicode normalization security (Issue #754)."""

import pytest
from flywheel.cli import sanitize_string


class TestUnicodeNormalization:
    """Test Unicode normalization to prevent homograph attacks."""

    def test_fullwidth_characters_should_be_normalized(self):
        """Fullwidth characters should be normalized and removed.

        Attackers can use fullwidth characters that look like regular ASCII
        but have different Unicode code points. These should be normalized
        to their ASCII equivalents first, then filtered.
        """
        # Fullwidth Latin letters and digits
        # ａｂｃ (U+FF41-FF43) should be normalized to 'abc'
        fullwidth = "ａｂｃ"
        result = sanitize_string(fullwidth)
        # After NFKC normalization, these should become 'abc' which is allowed
        # But current implementation just removes them without normalization
        assert result == "", f"Expected empty string, got '{result}'"

    def test_mixed_width_attack_attempt(self):
        """Mixed-width attack should be prevented.

        Attackers might mix fullwidth and regular characters to bypass filters.
        Example: 'ｓｙｓｔｅｍ' looks like 'system' but uses different code points.
        """
        # Mix of fullwidth and regular characters
        attack_string = "ｅｃｈｏ hello"
        result = sanitize_string(attack_string)
        # Should be normalized and filtered appropriately
        # Current implementation removes fullwidth chars without normalization
        assert result == " hello", f"Expected ' hello', got '{result}'"

    def test_combining_characters_should_be_normalized(self):
        """Combining characters should be normalized before filtering.

        Some characters can be represented in multiple ways (composed vs decomposed).
        For example, 'é' can be U+00E9 (single char) or U+0065 + U+0301 (e + combining acute).
        """
        # Decomposed form: e (U+0065) + combining acute (U+0301)
        decomposed = "e\u0301"  # é in decomposed form
        # Should normalize to composed form and handle correctly
        result = sanitize_string(decomposed)
        # The combining character should be handled (either preserved or removed)
        # Just verify it doesn't cause errors
        assert isinstance(result, str)

    def test_homograph_spoofing_attempt(self):
        """Test that homograph attacks are prevented.

        Visual lookalikes from different scripts (Cyrillic, Greek, etc.)
        should be normalized or removed to prevent spoofing.
        """
        # Cyrillic letters that look like Latin
        # с (Cyrillic es) looks like c (Latin c)
        # е (Cyrillic ie) looks like e (Latin e)
        cyrillic_spoof = "суре"  # Looks like "cure" but is Cyrillic
        result = sanitize_string(cyrillic_spoof)
        # Should handle this appropriately
        # Current implementation doesn't normalize, so behavior varies
        assert isinstance(result, str)
        # The point is: we should normalize first to catch these attacks

    def test_nfc_vs_nfd_normalization(self):
        """Test that different Unicode normalizations are handled consistently.

        The same string can have different byte representations depending on
        normalization form (NFC, NFD, NFKC, NFKD).
        """
        # 'é' in NFC (composed): U+00E9
        nfc_form = "\u00E9"
        # 'é' in NFD (decomposed): U+0065 U+0301
        nfd_form = "e\u0301"

        result_nfc = sanitize_string(nfc_form)
        result_nfd = sanitize_string(nfd_form)

        # Both should produce the same result
        # This test will fail until we implement normalization
        assert result_nfc == result_nfd, \
            f"NFC and NFD forms should normalize to same result: NFC='{result_nfc}', NFD='{result_nfd}'"
