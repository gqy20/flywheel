"""Tests for Unicode surrogate character sanitization (Issue #7023).

Unicode surrogate characters (U+D800-U+DFFF) are invalid when appearing
alone (not as part of a surrogate pair). They should be escaped to
prevent encoding issues and potential security vulnerabilities.
"""

from flywheel.formatter import _sanitize_text


class TestSurrogateSanitization:
    """Test that lone surrogate characters (0xD800-0xDFFF) are properly escaped."""

    def test_sanitize_text_escapes_lone_high_surrogate_start(self):
        """Test that the start of high surrogate range (0xD800) is escaped."""
        # High surrogate start
        assert _sanitize_text("text\ud800after") == r"text\ud800after"

    def test_sanitize_text_escapes_lone_high_surrogate_end(self):
        """Test that the end of high surrogate range (0xDBFF) is escaped."""
        # High surrogate end
        assert _sanitize_text("text\udbffafter") == r"text\udbffafter"

    def test_sanitize_text_escapes_lone_low_surrogate_start(self):
        """Test that the start of low surrogate range (0xDC00) is escaped."""
        # Low surrogate start
        assert _sanitize_text("text\udc00after") == r"text\udc00after"

    def test_sanitize_text_escapes_lone_low_surrogate_end(self):
        """Test that the end of low surrogate range (0xDFFF) is escaped."""
        # Low surrogate end
        assert _sanitize_text("text\udfffafter") == r"text\udfffafter"

    def test_sanitize_text_escapes_multiple_lone_surrogates(self):
        """Test that multiple lone surrogates are all escaped."""
        # Mix of high and low surrogates
        assert _sanitize_text("\ud800\udc00\udfff") == r"\ud800\udc00\udfff"

    def test_sanitize_text_surrogate_with_other_controls(self):
        """Test that surrogates are escaped alongside other control characters."""
        # Mix of surrogate and C1 control
        assert _sanitize_text("a\ud800b\x80c") == r"a\ud800b\x80c"

    def test_format_todo_escapes_surrogate_chars(self):
        """Test that format_todo properly escapes surrogate characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="Buy milk\ud800", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy milk\ud800"

    def test_valid_emoji_passes_through_unchanged(self):
        """Test that valid emoji (which uses surrogate pairs in UTF-16) still works."""
        # Emoji characters should pass through unchanged in Python 3
        # since Python strings use Unicode code points, not UTF-16
        assert _sanitize_text("🎉") == "🎉"
        assert _sanitize_text("😀") == "😀"
        assert _sanitize_text("🚀") == "🚀"

    def test_valid_unicode_above_bmp_passes_through(self):
        """Test that valid Unicode characters above BMP pass through unchanged."""
        # Characters above U+FFFF (BMP) should work fine
        assert _sanitize_text("𝕳𝖊𝖑𝖑𝖔") == "𝕳𝖊𝖑𝖑𝖔"  # Mathematical bold characters
        assert _sanitize_text("🎵") == "🎵"  # Musical note
