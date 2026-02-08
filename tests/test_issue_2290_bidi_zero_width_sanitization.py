"""Regression tests for Issue #2290: Unicode bidirectional override and zero-width character sanitization.

This test file ensures that Unicode bidirectional override characters (U+202A-U+202E, U+2066-U+2069)
and zero-width characters (U+200B-U+200D, U+FEFF) are properly escaped to prevent text spoofing attacks.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidiOverrideSanitization:
    """Test that bidirectional override characters (U+202A-U+202E) are properly escaped."""

    def test_sanitize_text_escapes_u202a_lre(self):
        """Test that U+202A LEFT-TO-RIGHT EMBEDDING is escaped."""
        # U+202A LRE can be used to manipulate text display
        text = "normal\u202aafter"
        result = _sanitize_text(text)
        assert "\\u202a" in result.lower()
        assert "\u202a" not in result

    def test_sanitize_text_escapes_u202b_rle(self):
        """Test that U+202B RIGHT-TO-LEFT EMBEDDING is escaped."""
        text = "normal\u202bafter"
        result = _sanitize_text(text)
        assert "\\u202b" in result.lower()
        assert "\u202b" not in result

    def test_sanitize_text_escapes_u202c_pdf(self):
        """Test that U+202C POP DIRECTIONAL FORMATTING is escaped."""
        text = "text\u202cmore"
        result = _sanitize_text(text)
        assert "\\u202c" in result.lower()
        assert "\u202c" not in result

    def test_sanitize_text_escapes_u202d_lro(self):
        """Test that U+202D LEFT-TO-RIGHT OVERRIDE is escaped."""
        text = "normal\u202dafter"
        result = _sanitize_text(text)
        assert "\\u202d" in result.lower()
        assert "\u202d" not in result

    def test_sanitize_text_escapes_u202e_rlo(self):
        """Test that U+202E RIGHT-TO-LEFT OVERRIDE is escaped."""
        # U+202E RLO is commonly used in text spoofing attacks
        text = "file.txt\u202eexe"
        result = _sanitize_text(text)
        assert "\\u202e" in result.lower()
        assert "\u202e" not in result


class TestBidiIsolateSanitization:
    """Test that bidirectional isolate characters (U+2066-U+2069) are properly escaped."""

    def test_sanitize_text_escapes_u2066_lri(self):
        """Test that U+2066 LEFT-TO-RIGHT ISOLATE is escaped."""
        text = "text\u2066more"
        result = _sanitize_text(text)
        assert "\\u2066" in result.lower()
        assert "\u2066" not in result

    def test_sanitize_text_escapes_u2067_rli(self):
        """Test that U+2067 RIGHT-TO-LEFT ISOLATE is escaped."""
        text = "text\u2067more"
        result = _sanitize_text(text)
        assert "\\u2067" in result.lower()
        assert "\u2067" not in result

    def test_sanitize_text_escapes_u2068_fsi(self):
        """Test that U+2068 FIRST STRONG ISOLATE is escaped."""
        text = "text\u2068more"
        result = _sanitize_text(text)
        assert "\\u2068" in result.lower()
        assert "\u2068" not in result

    def test_sanitize_text_escapes_u2069_pdi(self):
        """Test that U+2069 POP DIRECTIONAL ISOLATE is escaped."""
        text = "text\u2069more"
        result = _sanitize_text(text)
        assert "\\u2069" in result.lower()
        assert "\u2069" not in result


class TestZeroWidthCharacterSanitization:
    """Test that zero-width characters (U+200B-U+200D, U+FEFF) are properly escaped."""

    def test_sanitize_text_escapes_u200b_zwsp(self):
        """Test that U+200B ZERO-WIDTH SPACE is escaped."""
        text = "before\u200bafter"
        result = _sanitize_text(text)
        assert "\\u200b" in result.lower()
        assert "\u200b" not in result

    def test_sanitize_text_escapes_u200c_zwnj(self):
        """Test that U+200C ZERO-WIDTH NON-JOINER is escaped."""
        text = "before\u200cafter"
        result = _sanitize_text(text)
        assert "\\u200c" in result.lower()
        assert "\u200c" not in result

    def test_sanitize_text_escapes_u200d_zwj(self):
        """Test that U+200D ZERO-WIDTH JOINER is escaped."""
        text = "before\u200dafter"
        result = _sanitize_text(text)
        assert "\\u200d" in result.lower()
        assert "\u200d" not in result

    def test_sanitize_text_escapes_ufeff_zwnbsp(self):
        """Test that U+FEFF ZERO-WIDTH NO-BREAK SPACE (BOM) is escaped."""
        text = "before\ufeffafter"
        result = _sanitize_text(text)
        assert "\\ufeff" in result.lower()
        assert "\ufeff" not in result


class TestLegitimateRtlTextPreserved:
    """Test that legitimate right-to-left text (Arabic, Hebrew) is preserved."""

    def test_sanitize_text_preserves_arabic(self):
        """Legitimate Arabic text should pass through unchanged."""
        # Arabic text (not bidi control chars)
        arabic = "مرحبا بالعالم"
        result = _sanitize_text(arabic)
        assert result == arabic

    def test_sanitize_text_preserves_hebrew(self):
        """Legitimate Hebrew text should pass through unchanged."""
        # Hebrew text (not bidi control chars)
        hebrew = "שלום עולם"
        result = _sanitize_text(hebrew)
        assert result == hebrew

    def test_sanitize_text_preserves_mixed_rtl_content(self):
        """Mixed legitimate RTL content should be preserved."""
        mixed = "Hello مرحبا"
        result = _sanitize_text(mixed)
        assert result == mixed


class TestTodoFormatterBidiSanitization:
    """Test that TodoFormatter properly sanitizes bidi and zero-width characters."""

    def test_format_todo_escapes_bidi_override(self):
        """Todo with U+202E RLO should be escaped in output."""
        todo = Todo(id=1, text="file.txt\u202eexe", done=False)
        result = TodoFormatter.format_todo(todo)
        # Should contain escaped representation
        assert "\\u202e" in result.lower()
        # Should not contain actual bidi character
        assert "\u202e" not in result

    def test_format_todo_escapes_zero_width_space(self):
        """Todo with U+200B ZWSP should be escaped in output."""
        todo = Todo(id=1, text="task\u200bhidden", done=False)
        result = TodoFormatter.format_todo(todo)
        # Should contain escaped representation
        assert "\\u200b" in result.lower()
        # Should not contain actual zero-width character
        assert "\u200b" not in result

    def test_format_todo_spoofing_attack_prevented(self):
        """Test that a common spoofing attack vector is prevented."""
        # This attack makes "exe.txt" appear as "txt.exe" by using RLO
        # The RLO character reverses the display of the following text
        malicious = "innocuous.txt\u202egpj"
        todo = Todo(id=1, text=malicious, done=False)
        result = TodoFormatter.format_todo(todo)
        # The RLO should be escaped, revealing the true filename
        assert "\\u202e" in result.lower()


class TestCombinedControlCharacters:
    """Test sanitization of mixed control characters including bidi and zero-width."""

    def test_sanitize_text_mixed_controls(self):
        """Test that bidi, zero-width, and ASCII control chars are all escaped."""
        # Mix of C0 control, C1 control, bidi override, and zero-width
        text = "start\n\x9f\u202e\u200bend"
        result = _sanitize_text(text)
        # All should be escaped
        assert "\\n" in result
        assert "\\x9f" in result
        assert "\\u202e" in result.lower()
        assert "\\u200b" in result.lower()

    def test_format_todo_with_mixed_malicious_chars(self):
        """Todo with multiple types of malicious characters."""
        todo = Todo(id=1, text="task\x1b[31m\u202e\u200b", done=False)
        result = TodoFormatter.format_todo(todo)
        # All malicious chars should be escaped
        assert "\\x1b" in result
        assert "\\u202e" in result.lower()
        assert "\\u200b" in result.lower()
