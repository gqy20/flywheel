"""Tests for zero-width and invisible Unicode character sanitization (Issue #5177).

Zero-width and invisible Unicode characters can be used for visual spoofing attacks
by hiding malicious content in what appears to be normal text. These characters
should be escaped to visible representations.
"""

from flywheel.formatter import _sanitize_text


class TestInvisibleUnicodeSanitization:
    """Test that zero-width and invisible Unicode characters are properly escaped."""

    def test_sanitize_text_escapes_zero_width_space_u200b(self):
        """Test that zero-width space (U+200B) is escaped."""
        assert _sanitize_text("\u200b") == r"\u200b"
        assert _sanitize_text("hello\u200bworld") == r"hello\u200bworld"

    def test_sanitize_text_escapes_zero_width_joiner_u200d(self):
        """Test that zero-width joiner (U+200D) is escaped."""
        assert _sanitize_text("\u200d") == r"\u200d"
        assert _sanitize_text("text\u200djoin") == r"text\u200djoin"

    def test_sanitize_text_escapes_bom_ufeff(self):
        """Test that BOM (U+FEFF) is escaped."""
        assert _sanitize_text("\ufeff") == r"\ufeff"
        assert _sanitize_text("\ufeffprefix") == r"\ufeffprefix"

    def test_sanitize_text_escapes_word_joiner_u2060(self):
        """Test that word joiner (U+2060) is escaped."""
        assert _sanitize_text("\u2060") == r"\u2060"
        assert _sanitize_text("word\u2060join") == r"word\u2060join"

    def test_sanitize_text_escapes_multiple_invisible_chars(self):
        """Test that multiple invisible characters are all escaped."""
        # A string with multiple invisible chars
        result = _sanitize_text("a\u200bb\u200dc\ufeffd\u2060e")
        assert result == r"a\u200bb\u200dc\ufeffd\u2060e"

    def test_sanitize_text_escapes_zero_width_non_joiner_u200c(self):
        """Test that zero-width non-joiner (U+200C) is escaped."""
        assert _sanitize_text("\u200c") == r"\u200c"

    def test_sanitize_text_escapes_left_to_right_mark_u200e(self):
        """Test that left-to-right mark (U+200E) is escaped."""
        assert _sanitize_text("\u200e") == r"\u200e"

    def test_sanitize_text_escapes_right_to_left_mark_u200f(self):
        """Test that right-to-left mark (U+200F) is escaped."""
        assert _sanitize_text("\u200f") == r"\u200f"

    def test_format_todo_escapes_invisible_unicode(self):
        """Test that format_todo properly escapes invisible Unicode characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="Buy\u200bmilk", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy\u200bmilk"

    def test_normal_unicode_not_affected(self):
        """Test that normal visible Unicode characters pass through unchanged."""
        # Regular unicode characters should not be affected
        assert _sanitize_text("café") == "café"
        assert _sanitize_text("🎉") == "🎉"
        assert _sanitize_text("你好") == "你好"
