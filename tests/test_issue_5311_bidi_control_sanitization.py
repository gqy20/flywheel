"""Regression tests for Issue #5311: Unicode Bidi control character sanitization.

This test file ensures that Unicode Bidirectional (Bidi) control characters
are properly escaped to prevent terminal text manipulation attacks.

Bidi control characters can be used to display text differently than it
actually reads, which can be exploited for security attacks.

Unicode Bidi control ranges:
- LRE/LRM/RLE/RLM: U+200E-U+200F
- LRE/RLE/PDF/LRO/RLO: U+202A-U+202E
- LRI/RLI/FSI/PDI: U+2066-U+2069
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidiControlSanitization:
    """Test that Unicode Bidi control characters are properly escaped."""

    def test_sanitize_text_escapes_lrm_u200e(self):
        """Test that Left-to-Right Mark (U+200E) is escaped."""
        assert _sanitize_text("text\u200eafter") == r"text\u200eafter"

    def test_sanitize_text_escapes_rlm_u200f(self):
        """Test that Right-to-Left Mark (U+200F) is escaped."""
        assert _sanitize_text("text\u200fafter") == r"text\u200fafter"

    def test_sanitize_text_escapes_lre_u202a(self):
        """Test that Left-to-Right Embedding (U+202A) is escaped."""
        assert _sanitize_text("text\u202aafter") == r"text\u202aafter"

    def test_sanitize_text_escapes_rle_u202b(self):
        """Test that Right-to-Left Embedding (U+202B) is escaped."""
        assert _sanitize_text("text\u202bafter") == r"text\u202bafter"

    def test_sanitize_text_escapes_pdf_u202c(self):
        """Test that Pop Directional Format (U+202C) is escaped."""
        assert _sanitize_text("text\u202cafter") == r"text\u202cafter"

    def test_sanitize_text_escapes_lro_u202d(self):
        """Test that Left-to-Right Override (U+202D) is escaped."""
        assert _sanitize_text("text\u202dafter") == r"text\u202dafter"

    def test_sanitize_text_escapes_rlo_u202e(self):
        """Test that Right-to-Left Override (U+202E) is escaped.

        U+202E (RLO) is particularly dangerous as it can reverse text display.
        """
        assert _sanitize_text("\u202e") == r"\u202e"

    def test_sanitize_text_escapes_lri_u2066(self):
        """Test that Left-to-Right Isolate (U+2066) is escaped."""
        assert _sanitize_text("text\u2066after") == r"text\u2066after"

    def test_sanitize_text_escapes_rli_u2067(self):
        """Test that Right-to-Left Isolate (U+2067) is escaped."""
        assert _sanitize_text("text\u2067after") == r"text\u2067after"

    def test_sanitize_text_escapes_fsi_u2068(self):
        """Test that First Strong Isolate (U+2068) is escaped."""
        assert _sanitize_text("text\u2068after") == r"text\u2068after"

    def test_sanitize_text_escapes_pdi_u2069(self):
        """Test that Pop Directional Isolate (U+2069) is escaped."""
        assert _sanitize_text("\u2069") == r"\u2069"

    def test_sanitize_text_escapes_multiple_bidi_chars(self):
        """Test that multiple Bidi control characters are all escaped."""
        # Mix of characters from all three Bidi ranges
        result = _sanitize_text("\u200e\u202e\u2069")
        assert result == r"\u200e\u202e\u2069"

    def test_sanitize_text_bidi_with_other_controls(self):
        """Test that Bidi chars are escaped alongside other control characters."""
        # Mix of C0, C1, DEL, and Bidi controls
        assert _sanitize_text("a\u200eb\x80c\u202ed") == r"a\u200eb\x80c\u202ed"

    def test_format_todo_escapes_rlo_attack(self):
        """Test that RLO-based text spoofing attacks are prevented.

        A classic attack: display "exe.txt" when the actual filename is "txt.exe".
        """
        # Using RLO to try to make "txt.exe" display as "exe.txt"
        todo = Todo(id=1, text="Download exe\u202etxt.exe")
        result = TodoFormatter.format_todo(todo)
        assert r"\u202e" in result
        # The RLO character should NOT be present unescaped
        assert "\u202e" not in result

    def test_format_todo_escapes_full_bidi_range(self):
        """Test that format_todo escapes all Bidi ranges."""
        todo = Todo(id=1, text="\u200e\u202a\u2066")
        result = TodoFormatter.format_todo(todo)
        assert r"\u200e" in result
        assert r"\u202a" in result
        assert r"\u2066" in result
