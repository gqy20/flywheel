"""Tests for Unicode surrogate character sanitization (Issue #7023).

Unicode surrogate characters (U+D800-U+DFFF) are invalid when appearing alone
in UTF-8 encoded strings. They are only valid as pairs in UTF-16 encoding.
Lone surrogates can cause encoding errors and should be sanitized.
"""

from flywheel.formatter import _sanitize_text


class TestSurrogateSanitization:
    """Test that lone surrogate characters (0xD800-0xDFFF) are properly escaped."""

    def test_sanitize_text_escapes_lone_high_surrogate(self):
        """Test that lone high surrogates (0xD800-0xDBFF) are escaped."""
        # Start of high surrogate range (0xD800)
        assert _sanitize_text("text\ud800after") == r"text\ud800after"
        # End of high surrogate range (0xDBFF)
        assert _sanitize_text("normal\udbffend") == r"normal\udbffend"

    def test_sanitize_text_escapes_lone_low_surrogate(self):
        """Test that lone low surrogates (0xDC00-0xDFFF) are escaped."""
        # Start of low surrogate range (0xDC00)
        assert _sanitize_text("test\udc00") == r"test\udc00"
        # End of low surrogate range (0xDFFF)
        assert _sanitize_text("\udfff test") == r"\udfff test"

    def test_sanitize_text_escapes_individual_surrogate_chars(self):
        """Test specific surrogate characters."""
        # High surrogate (0xD800)
        assert _sanitize_text("test\ud800") == r"test\ud800"
        # Low surrogate (0xDC00)
        assert _sanitize_text("\udc00test") == r"\udc00test"
        # Another surrogate (0xDFFF)
        assert _sanitize_text("x\udfffy") == r"x\udfffy"

    def test_sanitize_text_surrogate_with_other_controls(self):
        """Test that surrogates are escaped alongside other control characters."""
        # Mix of C0, C1, DEL, and surrogate
        assert _sanitize_text("a\x01b\ud800c") == r"a\x01b\ud800c"
        # Surrogate with C1 control
        assert _sanitize_text("\ud800\x9f") == r"\ud800\x9f"

    def test_format_todo_escapes_surrogate_chars(self):
        """Test that format_todo properly escapes surrogate characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="Buy milk\ud800", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy milk\ud800"

    def test_valid_emoji_still_works(self):
        """Test that valid emoji (properly encoded) still works.

        In Python 3, strings are Unicode code points. Emoji like 🎉 are
        stored as single code points (U+1F389), not as surrogate pairs.
        Surrogate pairs only exist in UTF-16 encoding.
        """
        # These are valid Unicode characters, not surrogates
        assert _sanitize_text("🎉") == "🎉"
        assert _sanitize_text("😀") == "😀"
        assert _sanitize_text("🚀") == "🚀"

    def test_full_surrogate_range_covered(self):
        """Test that the full surrogate range (0xD800-0xDFFF) is escaped."""
        # Test boundaries and some middle values
        for code in [0xD800, 0xDA00, 0xDBFF, 0xDC00, 0xDE00, 0xDFFF]:
            char = chr(code)
            result = _sanitize_text(char)
            # Should be escaped as \uXXXX
            assert result == f"\\u{code:04x}", f"Expected \\u{code:04x} for U+{code:04X}"
