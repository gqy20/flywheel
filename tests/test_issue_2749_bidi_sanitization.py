"""Regression tests for Issue #2749: Unicode bidirectional override character sanitization.

This test file ensures that Unicode bidirectional override characters (U+202A-U+202E,
U+2066-U+2069) and zero-width characters (U+200B-U+200D, U+2060-U+2063) are properly
escaped to prevent text spoofing attacks (Trojan Source style attacks).
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidiOverrideSanitization:
    """Test that bidirectional override characters are properly escaped."""

    def test_sanitize_text_escapes_rtl_override_u202e(self):
        """Test that RTL override (U+202E) is escaped."""
        # U+202E = RIGHT-TO-LEFT OVERRIDE
        text = "admin\u202E@example.com"
        result = _sanitize_text(text)
        assert r"\u202e" in result.lower()
        # Should not contain the actual bidi character
        assert "\u202E" not in result

    def test_sanitize_text_escapes_ltr_override_u202d(self):
        """Test that LTR override (U+202D) is escaped."""
        # U+202D = LEFT-TO-RIGHT OVERRIDE
        text = "test\u202Dtext"
        result = _sanitize_text(text)
        assert r"\u202d" in result.lower()
        assert "\u202D" not in result

    def test_sanitize_text_escapes_ltr_embedding_u202a(self):
        """Test that LTR embedding (U+202A) is escaped."""
        # U+202A = LEFT-TO-RIGHT EMBEDDING
        text = "start\u202Aend"
        result = _sanitize_text(text)
        assert r"\u202a" in result.lower()
        assert "\u202A" not in result

    def test_sanitize_text_escapes_rtl_embedding_u202b(self):
        """Test that RTL embedding (U+202B) is escaped."""
        # U+202B = RIGHT-TO-LEFT EMBEDDING
        text = "start\u202Bend"
        result = _sanitize_text(text)
        assert r"\u202b" in result.lower()
        assert "\u202B" not in result

    def test_sanitize_text_escapes_pop_direction_u202c(self):
        """Test that pop directional format (U+202C) is escaped."""
        # U+202C = POP DIRECTIONAL FORMAT
        text = "text\u202Cmore"
        result = _sanitize_text(text)
        assert r"\u202c" in result.lower()
        assert "\u202C" not in result


class TestBidiIsolateControls:
    """Test that bidirectional isolate controls are properly escaped."""

    def test_sanitize_text_escapes_ltr_isolate_u2066(self):
        """Test that LTR isolate (U+2066) is escaped."""
        # U+2066 = LEFT-TO-RIGHT ISOLATE
        text = "start\u2066end"
        result = _sanitize_text(text)
        assert r"\u2066" in result.lower()
        assert "\u2066" not in result

    def test_sanitize_text_escapes_rtl_isolate_u2067(self):
        """Test that RTL isolate (U+2067) is escaped."""
        # U+2067 = RIGHT-TO-LEFT ISOLATE
        text = "start\u2067end"
        result = _sanitize_text(text)
        assert r"\u2067" in result.lower()
        assert "\u2067" not in result

    def test_sanitize_text_escapes_first_strong_isolate_u2068(self):
        """Test that first strong isolate (U+2068) is escaped."""
        # U+2068 = FIRST STRONG ISOLATE
        text = "start\u2068end"
        result = _sanitize_text(text)
        assert r"\u2068" in result.lower()
        assert "\u2068" not in result

    def test_sanitize_text_escapes_pop_direction_isolate_u2069(self):
        """Test that pop direction isolate (U+2069) is escaped."""
        # U+2069 = POP DIRECTIONAL ISOLATE
        text = "text\u2069more"
        result = _sanitize_text(text)
        assert r"\u2069" in result.lower()
        assert "\u2069" not in result


class TestZeroWidthCharacters:
    """Test that zero-width characters are properly escaped."""

    def test_sanitize_text_escapes_zero_width_space_u200b(self):
        """Test that zero-width space (U+200B) is escaped."""
        # U+200B = ZERO WIDTH SPACE
        text = "test\u200Btext"
        result = _sanitize_text(text)
        assert r"\u200b" in result.lower()
        assert "\u200B" not in result

    def test_sanitize_text_escapes_zero_width_non_joiner_u200c(self):
        """Test that zero-width non-joiner (U+200C) is escaped."""
        # U+200C = ZERO WIDTH NON-JOINER
        text = "test\u200Ctext"
        result = _sanitize_text(text)
        assert r"\u200c" in result.lower()
        assert "\u200C" not in result

    def test_sanitize_text_escapes_zero_width_joiner_u200d(self):
        """Test that zero-width joiner (U+200D) is escaped."""
        # U+200D = ZERO WIDTH JOINER
        text = "test\u200Dtext"
        result = _sanitize_text(text)
        assert r"\u200d" in result.lower()
        assert "\u200D" not in result

    def test_sanitize_text_escapes_word_joiner_u2060(self):
        """Test that word joiner (U+2060) is escaped."""
        # U+2060 = WORD JOINER
        text = "test\u2060text"
        result = _sanitize_text(text)
        assert r"\u2060" in result.lower()
        assert "\u2060" not in result

    def test_sanitize_text_escapes_function_application_u2061(self):
        """Test that function application (U+2061) is escaped."""
        # U+2061 = FUNCTION APPLICATION
        text = "test\u2061text"
        result = _sanitize_text(text)
        assert r"\u2061" in result.lower()
        assert "\u2061" not in result

    def test_sanitize_text_escapes_invisible_times_u2062(self):
        """Test that invisible times (U+2062) is escaped."""
        # U+2062 = INVISIBLE TIMES
        text = "test\u2062text"
        result = _sanitize_text(text)
        assert r"\u2062" in result.lower()
        assert "\u2062" not in result

    def test_sanitize_text_escapes_invisible_separator_u2063(self):
        """Test that invisible separator (U+2063) is escaped."""
        # U+2063 = INVISIBLE SEPARATOR
        text = "test\u2063text"
        result = _sanitize_text(text)
        assert r"\u2063" in result.lower()
        assert "\u2063" not in result


class TestTrojanSourceAttack:
    """Test specific Trojan Source attack scenarios."""

    def test_trojan_source_email_spoof(self):
        """Test the classic Trojan Source email spoofing attack."""
        # The attacker makes "nimda@example.com" display as "admin@example.com"
        # by using RTL override to reverse the display
        text = "nimda\u202E@example.com"
        result = _sanitize_text(text)
        # The bidi override should be escaped
        assert r"\u202e" in result.lower()
        # The attack should not work in the escaped output
        assert "\u202E" not in result

    def test_format_todo_with_bidi_attack(self):
        """Test that format_todo properly escapes bidi attacks in todo text."""
        # Simulate an attacker trying to hide malicious text
        todo = Todo(id=1, text="Buy milk\u202E] [x] MALICIOUS", done=False)
        result = TodoFormatter.format_todo(todo)
        # The bidi override should be escaped
        assert r"\u202e" in result.lower()
        # Should not contain the actual bidi character
        assert "\u202E" not in result


class TestExistingControlCharSanitization:
    """Verify existing control character sanitization still works."""

    def test_existing_control_chars_still_escaped(self):
        """Test that existing control character escaping still works."""
        # This ensures our changes don't break existing functionality
        assert _sanitize_text("test\n") == r"test\n"
        assert _sanitize_text("test\r") == r"test\r"
        assert _sanitize_text("test\t") == r"test\t"
        assert _sanitize_text("test\x00") == r"test\x00"

    def test_normal_unicode_passes_through(self):
        """Test that normal Unicode text is not affected."""
        # Normal Unicode should pass through unchanged
        assert _sanitize_text("café") == "café"
        assert _sanitize_text("日本語") == "日本語"
        assert _sanitize_text("🎉") == "🎉"
