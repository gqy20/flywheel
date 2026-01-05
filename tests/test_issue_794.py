"""Tests for Issue #794 - Unicode script filtering bypass risk."""

import pytest
from flywheel.cli import sanitize_string


class TestUnicodeScriptFiltering:
    """Test Unicode script filtering to prevent bypass vulnerabilities."""

    def test_latin_extended_characters_preserved(self):
        """Test that legitimate Latin extended characters are preserved."""
        # Latin Extended-A characters
        assert sanitize_string("āăąĉċčďđēėęě") == "āăąĉċčďđēėęě"

        # Latin Extended-B characters
        assert sanitize_string("ƀƁƂƃƄƅƆƇƈƉ") == "ƀƁƂƃƄƅƆƇƈƉ"

        # Latin Extended Additional
        assert sanitize_string("ḁḃḅḇḉḋḍḏ") == "ḁḃḅḇḉḋḍḏ"

        # Latin Extended-C
        assert sanitize_string("ⱠⱡⱢⱣⱤⱥ") == "ⱠⱡⱢⱣⱤⱥ"

        # Latin Extended-D
        assert sanitize_string("꜠꜡ꜢꜣꜤ") == "꜠꜡ꜢꜣꜤ"

        # Latin Extended-E
        assert sanitize_string("ꝰꝱꝲꝳ") == "ꝰꝱꝲꝳ"

    def test_mathematical_latin_characters_filtered(self):
        """Test that mathematical symbols (which may use Latin-like chars) are filtered."""
        # Mathematical bold characters should be filtered as they're not Latin script
        # These are in the Mathematical Alphanumeric Symbols block
        mathematical_bold = "𝐀𝐁𝐂𝐃𝐄𝐅"  # U+1D400-U+1D419
        # These should be filtered as they're not strictly Latin script
        # Even though they look like Latin, they're in a different Unicode block
        result = sanitize_string(mathematical_bold)
        assert result == "" or result != mathematical_bold

    def test_cyrillic_homographs_blocked(self):
        """Test that Cyrillic characters that look like Latin are blocked."""
        # These look like Latin but are Cyrillic
        assert sanitize_string("а") == ""  # Cyrillic а (U+0430), looks like Latin 'a'
        assert sanitize_string("б") == ""  # Cyrillic б (U+0431)
        assert sanitize_string("в") == ""  # Cyrillic в (U+0432), looks like Latin 'B'
        assert sanitize_string("г") == ""  # Cyrillic г (U+0433), looks like Latin 'r'
        assert sanitize_string("д") == ""  # Cyrillic д (U+0434)

    def test_greek_homographs_blocked(self):
        """Test that Greek characters that look like Latin are blocked."""
        # These look like Latin but are Greek
        assert sanitize_string("α") == ""  # Greek α (U+03B1), looks like Latin 'a'
        assert sanitize_string("β") == ""  # Greek β (U+03B2)
        assert sanitize_string("ε") == ""  # Greek ε (U+03B5), looks like Latin 'e'
        assert sanitize_string("ο") == ""  # Greek ο (U+03BF), looks like Latin 'o'
        assert sanitize_string("μ") == ""  # Greek μ (U+03BC), looks like Latin 'u'

    def test_latin_script_with_unicodedata_name(self):
        """Test that characters with LATIN in their Unicode name are preserved."""
        # Test various Latin characters that should be identified by their name
        test_cases = [
            ("À", "À"),  # LATIN CAPITAL LETTER A WITH GRAVE
            ("ß", "ß"),  # LATIN SMALL LETTER SHARP S
            ("Æ", "Æ"),  # LATIN CAPITAL LETTER AE
            ("œ", "œ"),  # LATIN SMALL LIGATURE OE
            ("č", "č"),  # LATIN SMALL LETTER C WITH CARON
        ]

        for input_char, expected in test_cases:
            result = sanitize_string(input_char)
            assert result == expected, f"Failed for {input_char} (U+{ord(input_char):04X})"

    def test_mixed_latin_and_non_latin(self):
        """Test string with mixed Latin and non-Latin characters."""
        # Latin + Cyrillic mixed
        assert sanitize_string("admin") == "admin"
        assert sanitize_string("аdmin") == "dmin"  # Cyrillic 'а' removed, Latin 'admin' kept
        assert sanitize_string("adminа") == "admin"  # Trailing Cyrillic removed

    def test_edge_cases(self):
        """Test edge cases for Unicode script filtering."""
        # Empty string
        assert sanitize_string("") == ""

        # Only non-Latin
        assert sanitize_string("你好世界") == ""  # Chinese
        assert sanitize_string("مرحبا") == ""  # Arabic
        assert sanitize_string("Привет") == ""  # Cyrillic

        # Special Latin combining marks
        # These should be kept as they're part of Latin script
        assert "é" in sanitize_string("café")
        assert "ñ" in sanitize_string("niño")
