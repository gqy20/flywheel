"""Tests for Unicode control character sanitization (Issue #3963).

Unicode bidirectional override characters (U+202A-U+202E) and zero-width
characters (U+200B-U+200F) can be used for text spoofing attacks in
terminal output. These should be sanitized to prevent potential security issues.
"""

from flywheel.formatter import _sanitize_text


class TestUnicodeControlSanitization:
    """Test that Unicode bidirectional and zero-width characters are escaped."""

    def test_sanitize_text_escapes_bidi_lre(self):
        """Test that Left-to-Right Embedding (U+202A) is escaped."""
        assert _sanitize_text("text\u202aafter") == r"text\u202aafter"

    def test_sanitize_text_escapes_bidi_rle(self):
        """Test that Right-to-Left Embedding (U+202B) is escaped."""
        assert _sanitize_text("text\u202bafter") == r"text\u202bafter"

    def test_sanitize_text_escapes_bidi_pdf(self):
        """Test that Pop Directional Format (U+202C) is escaped."""
        assert _sanitize_text("text\u202cafter") == r"text\u202cafter"

    def test_sanitize_text_escapes_bidi_lro(self):
        """Test that Left-to-Right Override (U+202D) is escaped."""
        assert _sanitize_text("text\u202dafter") == r"text\u202dafter"

    def test_sanitize_text_escapes_bidi_rlo(self):
        """Test that Right-to-Left Override (U+202E) is escaped.

        U+202E (RLO) is particularly dangerous as it can make text appear
        backwards, e.g., "exe\u202etxt" renders as "exe.txt" visually.
        """
        assert _sanitize_text("exe\u202etxt") == r"exe\u202etxt"

    def test_sanitize_text_escapes_zero_width_space(self):
        """Test that Zero Width Space (U+200B) is escaped."""
        assert _sanitize_text("text\u200bafter") == r"text\u200bafter"

    def test_sanitize_text_escapes_zero_width_non_joiner(self):
        """Test that Zero Width Non-Joiner (U+200C) is escaped."""
        assert _sanitize_text("text\u200cafter") == r"text\u200cafter"

    def test_sanitize_text_escapes_zero_width_joiner(self):
        """Test that Zero Width Joiner (U+200D) is escaped."""
        assert _sanitize_text("text\u200dafter") == r"text\u200dafter"

    def test_sanitize_text_escapes_left_to_right_mark(self):
        """Test that Left-to-Right Mark (U+200E) is escaped."""
        assert _sanitize_text("text\u200eafter") == r"text\u200eafter"

    def test_sanitize_text_escapes_right_to_left_mark(self):
        """Test that Right-to-Left Mark (U+200F) is escaped."""
        assert _sanitize_text("text\u200fafter") == r"text\u200fafter"

    def test_sanitize_text_multiple_unicode_controls(self):
        """Test that multiple Unicode control characters are all escaped."""
        # Mix of bidirectional and zero-width characters
        assert _sanitize_text("a\u202eb\u200bc") == r"a\u202eb\u200bc"

    def test_format_todo_escapes_unicode_control_chars(self):
        """Test that format_todo properly escapes Unicode control characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        # RLO character - this is the most dangerous for spoofing
        todo = Todo(id=1, text="Buy\u202emilk", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy\u202emilk"

    def test_sanitize_text_mixed_control_chars(self):
        """Test that Unicode controls are escaped alongside C0/C1 controls."""
        # Mix of C0 (0x01), C1 (0x80), bidi (U+202E), and zero-width (U+200B)
        assert _sanitize_text("a\x01b\x80c\u202ed\u200be") == r"a\x01b\x80c\u202ed\u200be"
