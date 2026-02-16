"""Regression tests for Issue #3846: Bidirectional text control character sanitization.

This test file ensures that Unicode bidirectional formatting characters and
zero-width characters are properly escaped to prevent visual spoofing attacks
(Trojan Source attacks).

Bidirectional control characters (U+202A-U+202E, U+200E, U+200F) can reorder
displayed text to hide malicious content. Zero-width characters (U+200B-U+200D,
U+2060, U+FEFF) can be used to obfuscate text.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidirectionalTextSanitization:
    """Test that bidirectional control characters are properly escaped."""

    def test_sanitize_text_escapes_rlo_u202e(self):
        """Test that Right-to-Left Override (U+202E) is escaped."""
        # RLO can reverse text display, hiding malicious content
        assert _sanitize_text("\u202e") == r"\u202e"
        assert _sanitize_text("Hello\u202eEvil") == r"Hello\u202eEvil"

    def test_sanitize_text_escapes_lro_u202d(self):
        """Test that Left-to-Right Override (U+202D) is escaped."""
        assert _sanitize_text("\u202d") == r"\u202d"
        assert _sanitize_text("Text\u202dMore") == r"Text\u202dMore"

    def test_sanitize_text_escapes_lre_u202a(self):
        """Test that Left-to-Right Embedding (U+202A) is escaped."""
        assert _sanitize_text("\u202a") == r"\u202a"

    def test_sanitize_text_escapes_rle_u202b(self):
        """Test that Right-to-Left Embedding (U+202B) is escaped."""
        assert _sanitize_text("\u202b") == r"\u202b"

    def test_sanitize_text_escapes_pdf_u202c(self):
        """Test that Pop Directional Formatting (U+202C) is escaped."""
        assert _sanitize_text("\u202c") == r"\u202c"

    def test_sanitize_text_escapes_lri_u2066(self):
        """Test that Left-to-Right Isolate (U+2066) is escaped."""
        assert _sanitize_text("\u2066") == r"\u2066"

    def test_sanitize_text_escapes_rli_u2067(self):
        """Test that Right-to-Left Isolate (U+2067) is escaped."""
        assert _sanitize_text("\u2067") == r"\u2067"

    def test_sanitize_text_escapes_fsi_u2068(self):
        """Test that First Strong Isolate (U+2068) is escaped."""
        assert _sanitize_text("\u2068") == r"\u2068"

    def test_sanitize_text_escapes_pdi_u2069(self):
        """Test that Pop Directional Isolate (U+2069) is escaped."""
        assert _sanitize_text("\u2069") == r"\u2069"

    def test_sanitize_text_escapes_lrm_u200e(self):
        """Test that Left-to-Right Mark (U+200E) is escaped."""
        assert _sanitize_text("\u200e") == r"\u200e"

    def test_sanitize_text_escapes_rlm_u200f(self):
        """Test that Right-to-Left Mark (U+200F) is escaped."""
        assert _sanitize_text("\u200f") == r"\u200f"


class TestZeroWidthCharacterSanitization:
    """Test that zero-width characters are properly escaped."""

    def test_sanitize_text_escapes_zwsp_u200b(self):
        """Test that Zero-Width Space (U+200B) is escaped."""
        assert _sanitize_text("\u200b") == r"\u200b"
        assert _sanitize_text("Hello\u200bWorld") == r"Hello\u200bWorld"

    def test_sanitize_text_escapes_zwnj_u200c(self):
        """Test that Zero-Width Non-Joiner (U+200C) is escaped."""
        assert _sanitize_text("\u200c") == r"\u200c"

    def test_sanitize_text_escapes_zwj_u200d(self):
        """Test that Zero-Width Joiner (U+200D) is escaped."""
        assert _sanitize_text("\u200d") == r"\u200d"

    def test_sanitize_text_escapes_wj_u2060(self):
        """Test that Word Joiner (U+2060) is escaped."""
        assert _sanitize_text("\u2060") == r"\u2060"

    def test_sanitize_text_escapes_bom_ufeff(self):
        """Test that Byte Order Mark / Zero-Width No-Break Space (U+FEFF) is escaped."""
        assert _sanitize_text("\ufeff") == r"\ufeff"


class TestTrojanSourceAttack:
    """Test protection against Trojan Source style attacks."""

    def test_sanitize_text_trojan_source_example(self):
        """Test that a typical Trojan Source attack is neutralized."""
        # Example: "Hello" followed by RLO then "dival" which displays as "lavid"
        # This could hide malicious code as a comment
        malicious = "/* Hello\u202e dival */"
        result = _sanitize_text(malicious)
        assert "\u202e" not in result
        assert r"\u202e" in result
        assert result == r"/* Hello\u202e dival */"

    def test_format_todo_with_bidirectional_attack(self):
        """Test that format_todo neutralizes bidirectional text attacks."""
        todo = Todo(id=1, text="Buy milk\u202eEvil\u202c")
        result = TodoFormatter.format_todo(todo)
        # Should contain escaped representation, not actual bidi chars
        assert r"\u202e" in result
        assert r"\u202c" in result
        assert "\u202e" not in result
        assert "\u202c" not in result

    def test_format_todo_with_zero_width_spoofing(self):
        """Test that format_todo neutralizes zero-width character spoofing."""
        # Hidden text using zero-width spaces
        todo = Todo(id=1, text="Buy\u200bmilk")
        result = TodoFormatter.format_todo(todo)
        assert r"\u200b" in result
        assert "\u200b" not in result

    def test_mixed_bidi_and_normal_unicode(self):
        """Test that normal Unicode passes through while bidi chars are escaped."""
        # Japanese text with embedded bidi character
        text = "日本語\u202eEnglish"
        result = _sanitize_text(text)
        assert "\u202e" not in result
        assert r"\u202e" in result
        assert "日本語" in result
        assert "English" in result
