"""Tests for C1 control character sanitization (Issue #2057).

C1 control characters (0x80-0x9f) are a set of control characters
that can be interpreted by some UTF-8 terminals for various commands.
They should be sanitized to prevent potential terminal manipulation attacks.
"""

from flywheel.formatter import _sanitize_text


class TestC1ControlSanitization:
    """Test that C1 control characters (0x80-0x9f) are properly escaped."""

    def test_sanitize_text_escapes_c1_control_chars_0x80_to_0x9f(self):
        """Test that the full C1 range (0x80-0x9f) is escaped."""
        # Test start of C1 range (0x80)
        assert _sanitize_text("text\x80after") == r"text\x80after"
        # Test end of C1 range (0x9f)
        assert _sanitize_text("normal\x9fend") == r"normal\x9fend"

    def test_sanitize_text_escapes_individual_c1_chars(self):
        """Test specific C1 control characters."""
        # PAD (0x80)
        assert _sanitize_text("test\x80") == r"test\x80"
        # ESC (0x1b is C0, but 0x9b is CSI - a C1 char)
        assert _sanitize_text("CSI\x9btest") == r"CSI\x9btest"
        # APC (0x9f)
        assert _sanitize_text("APC\x9f") == r"APC\x9f"

    def test_sanitize_text_c1_with_other_controls(self):
        """Test that C1 chars are escaped alongside other control characters."""
        # Mix of C0 (0x00-0x1f), C1 (0x80-0x9f), and DEL (0x7f)
        assert _sanitize_text("a\x01b\x80c\x7fd") == r"a\x01b\x80c\x7fd"
        assert _sanitize_text("\x9f\x1b\x80") == r"\x9f\x1b\x80"

    def test_format_todo_escapes_c1_chars(self):
        """Test that format_todo properly escapes C1 control characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="Buy milk\x9f", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 - Buy milk\x9f"

    def test_unicode_text_passes_through_unchanged(self):
        """Test that valid Unicode text is not affected by sanitization."""
        # Japanese characters
        assert _sanitize_text("こんにちは") == "こんにちは"
        # Accented characters
        assert _sanitize_text("café") == "café"
        # Emojis
        assert _sanitize_text("🎉") == "🎉"
        # Chinese characters
        assert _sanitize_text("你好") == "你好"

    def test_valid_multibyte_utf8_not_affected(self):
        """Test that valid multi-byte UTF-8 sequences pass through unchanged."""
        # Multi-byte UTF-8 sequences should NOT be escaped
        # Only actual C1 control characters (0x80-0x9f) should be escaped
        assert _sanitize_text("€") == "€"  # Euro sign (U+20AC) - multi-byte UTF8
        assert _sanitize_text("✓") == "✓"  # Check mark
        assert _sanitize_text("→") == "→"  # Arrow
