"""Tests for bidirectional text control character sanitization (Issue #3846).

Unicode bidirectional control characters (U+202A-U+202E) and zero-width
characters (U+200B-U+200F, U+2060, U+FEFF) can be used for visual spoofing
attacks (Trojan Source). They should be sanitized to prevent text rendering
manipulation.
"""

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidirectionalTextSanitization:
    """Test that bidirectional text control characters are properly escaped."""

    def test_sanitize_text_escapes_rlo_character(self):
        """Test that Right-to-Left Override (U+202E) is escaped."""
        # RLO can reverse text rendering to hide malicious content
        result = _sanitize_text("Hello\u202eEvil\u202c")
        assert "\\u202e" in result
        assert "\\u202c" in result
        # Should not contain actual characters
        assert "\u202e" not in result
        assert "\u202c" not in result

    def test_sanitize_text_escapes_lro_character(self):
        """Test that Left-to-Right Override (U+202D) is escaped."""
        result = _sanitize_text("text\u202dmore")
        assert "\\u202d" in result
        assert "\u202d" not in result

    def test_sanitize_text_escapes_all_bidi_formatting_chars(self):
        """Test all bidirectional formatting characters (U+202A-U+202E)."""
        # LRE (U+202A), RLE (U+202B), PDF (U+202C), LRO (U+202D), RLO (U+202E)
        for code in range(0x202A, 0x202F):
            char = chr(code)
            result = _sanitize_text(f"before{char}after")
            escaped = f"\\u{code:04x}"
            assert escaped in result, f"Character U+{code:04X} should be escaped"
            assert char not in result, f"Character U+{code:04X} should not be in output"

    def test_sanitize_text_escapes_direction_marks(self):
        """Test LRM (U+200E) and RLM (U+200F) direction marks."""
        # LRM (Left-to-Right Mark)
        result = _sanitize_text("text\u200e")
        assert "\\u200e" in result
        assert "\u200e" not in result

        # RLM (Right-to-Left Mark)
        result = _sanitize_text("text\u200f")
        assert "\\u200f" in result
        assert "\u200f" not in result

    def test_sanitize_text_escapes_zero_width_space(self):
        """Test that zero-width space (U+200B) is escaped."""
        result = _sanitize_text("text\u200bhidden")
        assert "\\u200b" in result
        assert "\u200b" not in result

    def test_sanitize_text_escapes_zero_width_joiner(self):
        """Test that zero-width joiner (U+200D) is escaped."""
        result = _sanitize_text("text\u200djoin")
        assert "\\u200d" in result
        assert "\u200d" not in result

    def test_sanitize_text_escapes_zero_width_non_joiner(self):
        """Test that zero-width non-joiner (U+200C) is escaped."""
        result = _sanitize_text("text\u200cnonjoin")
        assert "\\u200c" in result
        assert "\u200c" not in result

    def test_sanitize_text_escapes_word_joiner(self):
        """Test that word joiner (U+2060) is escaped."""
        result = _sanitize_text("text\u2060join")
        assert "\\u2060" in result
        assert "\u2060" not in result

    def test_sanitize_text_escapes_bom(self):
        """Test that BOM/zero-width no-break space (U+FEFF) is escaped."""
        result = _sanitize_text("\ufefftext")
        assert "\\ufeff" in result
        assert "\ufeff" not in result

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes bidirectional chars."""
        # Simulate Trojan Source attack: "Read" reversed to look like "daeR"
        todo = Todo(id=1, text="Read\u202edaeR\u202c file", done=False)
        result = TodoFormatter.format_todo(todo)
        assert "\\u202e" in result
        assert "\\u202c" in result
        # Should not contain actual bidi chars
        assert "\u202e" not in result
        assert "\u202c" not in result

    def test_sanitize_text_preserves_normal_unicode(self):
        """Test that normal Unicode text is not affected."""
        # Regular text with various scripts should pass through
        assert _sanitize_text("Hello World") == "Hello World"
        assert _sanitize_text("日本語") == "日本語"
        assert _sanitize_text("العربية") == "العربية"
        assert _sanitize_text("🎉🎊") == "🎉🎊"

    def test_sanitize_text_mixed_bidi_and_controls(self):
        """Test that bidi chars are escaped alongside other control characters."""
        # Mix of C0 (0x00-0x1f), bidi (U+202A-U+202E), zero-width (U+200B)
        result = _sanitize_text("a\x01b\u202ec\u200bd")
        assert "\\x01" in result
        assert "\\u202e" in result
        assert "\\u200b" in result
