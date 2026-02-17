"""Tests for Unicode bidirectional and zero-width character sanitization (Issue #3963).

Unicode bidirectional override characters (U+202A-U+202E) and zero-width characters
(U+200B-U+200F) can be used for text spoofing attacks. They should be sanitized
to prevent potential terminal output manipulation.
"""

from flywheel.formatter import _sanitize_text


class TestUnicodeBidiAndZeroWidthSanitization:
    """Test that Unicode bidirectional and zero-width characters are properly escaped."""

    def test_sanitize_text_escapes_bidi_lre_u202a(self):
        """Test that Left-to-Right Embedding (U+202A) is escaped."""
        # LRE - can be used to reverse text display direction
        assert _sanitize_text("text\u202aafter") == r"text\x202aafter"

    def test_sanitize_text_escapes_bidi_rle_u202b(self):
        """Test that Right-to-Left Embedding (U+202B) is escaped."""
        # RLE - can be used to reverse text display direction
        assert _sanitize_text("text\u202bafter") == r"text\x202bafter"

    def test_sanitize_text_escapes_bidi_pdf_u202c(self):
        """Test that Pop Directional Formatting (U+202C) is escaped."""
        # PDF - pops directional formatting state
        assert _sanitize_text("text\u202cafter") == r"text\x202cafter"

    def test_sanitize_text_escapes_bidi_lro_u202d(self):
        """Test that Left-to-Right Override (U+202D) is escaped."""
        # LRO - forces left-to-right text rendering
        assert _sanitize_text("text\u202dafter") == r"text\x202dafter"

    def test_sanitize_text_escapes_bidi_rlo_u202e(self):
        """Test that Right-to-Left Override (U+202E) is escaped."""
        # RLO - forces right-to-left text rendering, commonly used in spoofing attacks
        # Example: "C:\xe2\x80\xaetxt.exe" could appear as "C:\exe.txt"
        assert _sanitize_text("text\u202eafter") == r"text\x202eafter"

    def test_sanitize_text_escapes_zero_width_space_u200b(self):
        """Test that Zero-Width Space (U+200B) is escaped."""
        # ZWSP - invisible character that can break strings for spoofing
        assert _sanitize_text("text\u200bafter") == r"text\x200bafter"

    def test_sanitize_text_escapes_zero_width_non_joiner_u200c(self):
        """Test that Zero-Width Non-Joiner (U+200C) is escaped."""
        # ZWNJ - invisible character
        assert _sanitize_text("text\u200cafter") == r"text\x200cafter"

    def test_sanitize_text_escapes_zero_width_joiner_u200d(self):
        """Test that Zero-Width Joiner (U+200D) is escaped."""
        # ZWJ - invisible character used for emoji sequences
        assert _sanitize_text("text\u200dafter") == r"text\x200dafter"

    def test_sanitize_text_escapes_left_to_right_mark_u200e(self):
        """Test that Left-to-Right Mark (U+200E) is escaped."""
        # LRM - invisible directional mark
        assert _sanitize_text("text\u200eafter") == r"text\x200eafter"

    def test_sanitize_text_escapes_right_to_left_mark_u200f(self):
        """Test that Right-to-Left Mark (U+200F) is escaped."""
        # RLM - invisible directional mark
        assert _sanitize_text("text\u200fafter") == r"text\x200fafter"

    def test_sanitize_text_bidi_with_other_controls(self):
        """Test that bidi chars are escaped alongside other control characters."""
        # Mix of bidi override, zero-width, and existing control characters
        # Note: 0x01 uses 2 hex digits, higher values use 4 hex digits
        assert _sanitize_text("a\u202eb\u200bc\x01d") == r"a\x202eb\x200bc\x01d"

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes bidirectional characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        # Test with RLO which is the most dangerous for spoofing
        todo = Todo(id=1, text="C:\u202etxt.exe", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 C:\x202etxt.exe"

    def test_valid_unicode_not_affected(self):
        """Test that valid Unicode text outside dangerous ranges is not affected."""
        # Arabic text (which naturally contains RTL characters, but not control chars)
        assert _sanitize_text("مرحبا") == "مرحبا"
        # Hebrew text
        assert _sanitize_text("שלום") == "שלום"
        # Mixed RTL and LTR text
        assert _sanitize_text("Hello مرحبا World") == "Hello مرحبا World"
