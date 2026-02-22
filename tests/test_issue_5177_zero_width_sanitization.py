"""Tests for zero-width and invisible Unicode character sanitization (Issue #5177).

Zero-width and invisible Unicode characters can be used for visual spoofing
attacks by hiding malicious content in what appears to be normal text.
These characters should be escaped to visible representations.
"""

from flywheel.formatter import _sanitize_text


class TestZeroWidthSanitization:
    """Test that zero-width and invisible Unicode characters are properly escaped."""

    def test_sanitize_text_escapes_zero_width_space_u200b(self):
        """Test that zero-width space (U+200B) is escaped to visible representation."""
        assert _sanitize_text("text\u200bafter") == r"text\u200bafter"

    def test_sanitize_text_escapes_zero_width_joiner_u200d(self):
        """Test that zero-width joiner (U+200D) is escaped to visible representation."""
        assert _sanitize_text("text\u200dafter") == r"text\u200dafter"

    def test_sanitize_text_escapes_bom_ufeff(self):
        """Test that BOM (U+FEFF) is escaped to visible representation."""
        assert _sanitize_text("text\ufeffafter") == r"text\ufeffafter"

    def test_sanitize_text_escapes_word_joiner_u2060(self):
        """Test that word joiner (U+2060) is escaped to visible representation."""
        assert _sanitize_text("text\u2060after") == r"text\u2060after"

    def test_sanitize_text_escapes_multiple_zero_width_chars(self):
        """Test that multiple zero-width characters are all escaped."""
        assert _sanitize_text("a\u200bb\u200dc\ufeffd\u2060e") == r"a\u200bb\u200dc\ufeffd\u2060e"

    def test_sanitize_text_escapes_zero_width_at_boundaries(self):
        """Test zero-width characters at string start and end."""
        assert _sanitize_text("\u200bstart") == r"\u200bstart"
        assert _sanitize_text("end\u200b") == r"end\u200b"
        assert _sanitize_text("\ufeff") == r"\ufeff"

    def test_format_todo_escapes_zero_width_chars(self):
        """Test that format_todo properly escapes zero-width characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="Buy milk\u200b", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy milk\u200b"

    def test_zero_width_nonjoiner_u200c_escaped(self):
        """Test that zero-width non-joiner (U+200C) is escaped."""
        assert _sanitize_text("text\u200cafter") == r"text\u200cafter"

    def test_left_to_right_mark_u200e_escaped(self):
        """Test that left-to-right mark (U+200E) is escaped."""
        assert _sanitize_text("text\u200eafter") == r"text\u200eafter"

    def test_right_to_left_mark_u200f_escaped(self):
        """Test that right-to-left mark (U+200F) is escaped."""
        assert _sanitize_text("text\u200fafter") == r"text\u200fafter"

    def test_normal_unicode_not_affected(self):
        """Test that normal Unicode characters are not affected."""
        # Normal visible characters should pass through
        assert _sanitize_text("Hello World") == "Hello World"
        assert _sanitize_text("café") == "café"
        assert _sanitize_text("🎉") == "🎉"
