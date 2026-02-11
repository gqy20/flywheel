"""Regression tests for Issue #2749: Unicode bidirectional override character sanitization.

This test file ensures that Unicode bidirectional override characters and zero-width
characters are properly escaped to prevent text spoofing attacks (Trojan Source style).

The characters to sanitize:
- Bidirectional overrides: U+202A-U+202E (LRE, RLE, PDF, LRO, RLO)
- Isolate controls: U+2066-U+2069 (LRI, RLI, FSI, PDI)
- Zero-width characters: U+200B-U+200D (ZWSP, ZWNJ, ZWJ), U+2060-U+2063 (ZWNBSP, etc.)
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidiOverrideSanitization:
    """Test that Unicode bidirectional override characters are properly escaped."""

    def test_sanitize_text_escapes_rtl_override_u202e(self):
        """Test that U+202E (RIGHT-TO-LEFT OVERRIDE) is escaped."""
        # RTL override can make 'admin@example.com' display as 'nimda@example.com'
        result = _sanitize_text("normal\u202Ereversed")
        assert r"\u202e" in result.lower()
        # Should not contain actual bidi override character
        assert "\u202E" not in result

    def test_sanitize_text_escapes_ltr_override_u202d(self):
        """Test that U+202D (LEFT-TO-RIGHT OVERRIDE) is escaped."""
        result = _sanitize_text("normal\u202Dtext")
        assert r"\u202d" in result.lower()
        assert "\u202D" not in result

    def test_sanitize_text_escapes_rle_u202b(self):
        """Test that U+202B (RIGHT-TO-LEFT EMBEDDING) is escaped."""
        result = _sanitize_text("start\u202Bmiddle")
        assert r"\u202b" in result.lower()
        assert "\u202B" not in result

    def test_sanitize_text_escapes_lre_u202a(self):
        """Test that U+202A (LEFT-TO-RIGHT EMBEDDING) is escaped."""
        result = _sanitize_text("start\u202Amiddle")
        assert r"\u202a" in result.lower()
        assert "\u202A" not in result

    def test_sanitize_text_escapes_pdf_u202c(self):
        """Test that U+202C (POP DIRECTIONAL FORMAT) is escaped."""
        result = _sanitize_text("start\u202Cend")
        assert r"\u202c" in result.lower()
        assert "\u202C" not in result

    def test_sanitize_text_escapes_lri_u2066(self):
        """Test that U+2066 (LEFT-TO-RIGHT ISOLATE) is escaped."""
        result = _sanitize_text("text\u2066isolated")
        assert r"\u2066" in result
        assert "\u2066" not in result

    def test_sanitize_text_escapes_rli_u2067(self):
        """Test that U+2067 (RIGHT-TO-LEFT ISOLATE) is escaped."""
        result = _sanitize_text("text\u2067isolated")
        assert r"\u2067" in result
        assert "\u2067" not in result

    def test_sanitize_text_escapes_fsi_u2068(self):
        """Test that U+2068 (FIRST STRONG ISOLATE) is escaped."""
        result = _sanitize_text("text\u2068isolated")
        assert r"\u2068" in result
        assert "\u2068" not in result

    def test_sanitize_text_escapes_pdi_u2069(self):
        """Test that U+2069 (POP DIRECTIONAL ISOLATE) is escaped."""
        result = _sanitize_text("text\u2069end")
        assert r"\u2069" in result
        assert "\u2069" not in result


class TestZeroWidthCharacterSanitization:
    """Test that zero-width characters are properly escaped."""

    def test_sanitize_text_escapes_zero_width_space_u200b(self):
        """Test that U+200B (ZERO WIDTH SPACE) is escaped."""
        result = _sanitize_text("before\u200Bafter")
        assert r"\u200b" in result
        assert "\u200B" not in result

    def test_sanitize_text_escapes_zero_width_non_joiner_u200c(self):
        """Test that U+200C (ZERO WIDTH NON-JOINER) is escaped."""
        result = _sanitize_text("text\u200Cmore")
        assert r"\u200c" in result
        assert "\u200C" not in result

    def test_sanitize_text_escapes_zero_width_joiner_u200d(self):
        """Test that U+200D (ZERO WIDTH JOINER) is escaped."""
        result = _sanitize_text("text\u200Dmore")
        assert r"\u200d" in result
        assert "\u200D" not in result

    def test_sanitize_text_escapes_zwnbsp_u2060(self):
        """Test that U+2060 (ZERO WIDTH NO-BREAK SPACE) is escaped."""
        result = _sanitize_text("text\u2060more")
        assert r"\u2060" in result
        assert "\u2060" not in result

    def test_sanitize_text_escapes_word_joiner_u2061(self):
        """Test that U+2061 (FUNCTION APPLICATION) is escaped."""
        result = _sanitize_text("text\u2061more")
        assert r"\u2061" in result
        assert "\u2061" not in result

    def test_sanitize_text_escapes_invisible_separator_u2063(self):
        """Test that U+2063 (INVISIBLE SEPARATOR) is escaped."""
        result = _sanitize_text("text\u2063more")
        assert r"\u2063" in result
        assert "\u2063" not in result


class TestBidiWithTodoFormatter:
    """Test that bidi override characters are escaped in formatted output."""

    def test_format_todo_escapes_rtl_override_spoof(self):
        """Test that potential text spoofing via RTL override is prevented."""
        # This could be used to make "nimda@example.com" display as "admin@example.com"
        todo = Todo(id=1, text="User: moc.example@nimda\u202E", done=False)
        result = TodoFormatter.format_todo(todo)
        # The bidi override should be escaped
        assert r"\u202e" in result.lower()
        # The actual character should not be present
        assert "\u202E" not in result

    def test_format_todo_with_multiple_bidi_chars(self):
        """Test that multiple bidi override characters are all escaped."""
        todo = Todo(id=1, text="text\u202A\u202B\u202C\u202D\u202E", done=False)
        result = TodoFormatter.format_todo(todo)
        # All should be escaped
        assert r"\u202a" in result
        assert r"\u202b" in result
        assert r"\u202c" in result
        assert r"\u202d" in result
        assert r"\u202e" in result

    def test_format_todo_with_zero_width_chars(self):
        """Test that zero-width characters are escaped in formatted output."""
        todo = Todo(id=1, text="visible\u200B\u200C\u200Dhidden", done=False)
        result = TodoFormatter.format_todo(todo)
        assert r"\u200b" in result
        assert r"\u200c" in result
        assert r"\u200d" in result

    def test_format_todo_preserves_valid_unicode(self):
        """Test that valid Unicode is still preserved after bidi sanitization."""
        todo = Todo(id=1, text="Buy café and 日本語 and 🎉", done=False)
        result = TodoFormatter.format_todo(todo)
        assert "café" in result
        assert "日本語" in result
        assert "🎉" in result

    def test_format_todo_mixed_control_and_bidi(self):
        """Test that both control chars and bidi overrides are escaped together."""
        todo = Todo(id=1, text="text\nmore\u202Eend", done=False)
        result = TodoFormatter.format_todo(todo)
        assert r"\n" in result
        assert r"\u202e" in result.lower()


class TestBidiWithBackslashEscaping:
    """Test interaction between backslash escaping and bidi character escaping."""

    def test_backslash_escaped_before_bidi(self):
        """Test that backslashes are escaped before bidi characters."""
        # The backslash escape happens first to prevent collision
        result = _sanitize_text("\\path\u202E")
        # Backslash should be escaped first
        assert result.startswith(r"\\path")
        # Bidi override should be escaped
        assert r"\u202e" in result.lower()

    def test_literal_u_sequence_not_escaped(self):
        """Test that literal '\u202e' text is not confused with actual bidi char."""
        # This is literal text, not the actual control character
        result = _sanitize_text(r"text\u202E")
        # Should escape backslash
        assert r"\\u202E" in result
        # Should not double-escape
        assert result.count(r"\\u") >= 1
