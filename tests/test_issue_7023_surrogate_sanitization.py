"""Tests for Unicode surrogate character sanitization (Issue #7023).

Unicode surrogate characters (U+D800-U+DFFF) are invalid in UTF-8 and can
cause encoding errors, crashes, or undefined behavior when processed.
They should be sanitized to prevent potential issues.

Surrogates:
- High surrogates: U+D800-U+DBFF (used in UTF-16 for encoding code points > U+FFFF)
- Low surrogates: U+DC00-U+DFFF (used in UTF-16 paired with high surrogates)

These are invalid standalone characters in Unicode and should be escaped.
"""

from flywheel.formatter import _sanitize_text


class TestSurrogateSanitization:
    """Test that Unicode surrogate characters (U+D800-U+DFFF) are properly escaped."""

    def test_sanitize_text_escapes_high_surrogate_start(self):
        """Test that the start of high surrogate range (U+D800) is escaped."""
        # U+D800 is the first high surrogate
        assert _sanitize_text("text\ud800after") == r"text\ud800after"

    def test_sanitize_text_escapes_high_surrogate_end(self):
        """Test that the end of high surrogate range (U+DBFF) is escaped."""
        # U+DBFF is the last high surrogate
        assert _sanitize_text("normal\udbffend") == r"normal\udbffend"

    def test_sanitize_text_escapes_low_surrogate_start(self):
        """Test that the start of low surrogate range (U+DC00) is escaped."""
        # U+DC00 is the first low surrogate
        assert _sanitize_text("test\udc00") == r"test\udc00"

    def test_sanitize_text_escapes_low_surrogate_end(self):
        """Test that the end of low surrogate range (U+DFFF) is escaped."""
        # U+DFFF is the last low surrogate (and last of the entire surrogate range)
        assert _sanitize_text("\udfffend") == r"\udfffend"

    def test_sanitize_text_escapes_all_surrogates(self):
        """Test that various surrogates throughout the range are escaped."""
        # Test multiple surrogates at different points in the range
        assert _sanitize_text("a\ud800b\ud900c\uda00d\udb00e") == r"a\ud800b\ud900c\uda00d\udb00e"
        assert _sanitize_text("f\udc00g\udd00h\ude00i\udfffj") == r"f\udc00g\udd00h\ude00i\udfffj"

    def test_sanitize_text_surrogate_with_other_controls(self):
        """Test that surrogates are escaped alongside other control characters."""
        # Mix of C0 (0x01), C1 (0x80), DEL (0x7f), and surrogate (U+D800)
        assert _sanitize_text("a\x01b\x80c\x7fd\ud800e") == r"a\x01b\x80c\x7fd\ud800e"

    def test_format_todo_escapes_surrogate_chars(self):
        """Test that format_todo properly escapes surrogate characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="Buy milk\ud800", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy milk\ud800"

    def test_valid_unicode_not_affected(self):
        """Test that valid Unicode characters around the surrogate range are not affected."""
        # U+D7FF is just below surrogates (valid)
        assert _sanitize_text("\ud7ff") == "\ud7ff"
        # U+E000 is just above surrogates (valid, Private Use Area)
        assert _sanitize_text("\ue000") == "\ue000"
        # Regular CJK characters should pass through
        assert _sanitize_text("你好世界") == "你好世界"
        # Emojis should pass through
        assert _sanitize_text("🎉🚀✨") == "🎉🚀✨"
