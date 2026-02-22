"""Regression tests for Issue #5111: Unicode BiDi character sanitization.

BiDi (Bidirectional) characters can be used for text display manipulation attacks
where the visual appearance of text differs from its logical order.
For example, 'print("Read \u202eCMD.exe\u202c")' could appear as 'Read exe.CMD'.

This test file ensures that BiDi override characters are properly escaped
to prevent such visual spoofing attacks.

BiDi characters to escape:
- U+202A-U+202E: Bidirectional formatting characters
- U+2066-U+2069: Isolate formatting characters
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBiDiSanitization:
    """Test that Unicode BiDi characters are properly escaped."""

    def test_sanitize_text_escapes_rlo_bidi_override(self):
        """U+202E (Right-to-Left Override) should be escaped."""
        # This is the most dangerous BiDi character for spoofing
        result = _sanitize_text("Hello\u202eWorld")
        assert result == r"Hello\u202eWorld"
        assert "\u202e" not in result

    def test_sanitize_text_escapes_lro_bidi_override(self):
        """U+202D (Left-to-Right Override) should be escaped."""
        result = _sanitize_text("Text\u202dMore")
        assert result == r"Text\u202dMore"
        assert "\u202d" not in result

    def test_sanitize_text_escapes_all_bidi_range_202a_to_202e(self):
        """All characters in U+202A-U+202E range should be escaped."""
        for code in range(0x202A, 0x202F):
            char = chr(code)
            result = _sanitize_text(f"a{char}b")
            assert f"\\u{code:04x}" in result, f"U+{code:04X} not escaped"
            assert char not in result, f"U+{code:04X} still in result"

    def test_sanitize_text_escapes_all_bidi_isolate_range_2066_to_2069(self):
        """All characters in U+2066-U+2069 range should be escaped."""
        for code in range(0x2066, 0x206A):
            char = chr(code)
            result = _sanitize_text(f"a{char}b")
            assert f"\\u{code:04x}" in result, f"U+{code:04X} not escaped"
            assert char not in result, f"U+{code:04X} still in result"

    def test_sanitize_text_bidi_attack_example(self):
        """Test the example from the issue: EXEC\u202eNOT\u202c.exe."""
        # This would visually appear as "EXECexe.NOT" but is logically "EXEC\u202eNOT\u202c.exe"
        result = _sanitize_text("EXEC\u202eNOT\u202c.exe")
        # Should contain escaped representations, not raw BiDi chars
        assert "\\u202e" in result
        assert "\\u202c" in result
        assert "\u202e" not in result
        assert "\u202c" not in result

    def test_format_todo_escapes_bidi_in_text(self):
        """Todo with BiDi in text should output escaped representation."""
        todo = Todo(id=1, text="Buy milk\u202e[ ] FAKE_TODO")
        result = TodoFormatter.format_todo(todo)
        # Should contain escaped representation
        assert "\\u202e" in result
        # Should not contain actual BiDi character
        assert "\u202e" not in result

    def test_sanitize_text_bidi_with_other_controls(self):
        """Test that BiDi chars are escaped alongside other control characters."""
        # Mix of BiDi and ASCII control chars
        result = _sanitize_text("a\u202e\x01b\x7fc")
        assert "\\u202e" in result
        assert "\\x01" in result
        assert "\\x7f" in result
        # No actual control chars
        assert "\u202e" not in result
        assert "\x01" not in result
        assert "\x7f" not in result


class TestInvisibleFormattingSanitization:
    """Test that invisible formatting characters are properly escaped.

    These characters can also be used for visual spoofing:
    - U+200B-U+200F: Zero-width and direction characters
    - U+2060-U+2064: Word joiner and invisible operators
    - U+FEFF: Byte order mark / zero-width no-break space
    """

    def test_sanitize_text_escapes_zero_width_space(self):
        """U+200B (Zero Width Space) should be escaped."""
        result = _sanitize_text("Hello\u200bWorld")
        assert result == r"Hello\u200bWorld"
        assert "\u200b" not in result

    def test_sanitize_text_escapes_zero_width_non_joiner(self):
        """U+200C (Zero Width Non-Joiner) should be escaped."""
        result = _sanitize_text("Hello\u200cWorld")
        assert result == r"Hello\u200cWorld"
        assert "\u200c" not in result

    def test_sanitize_text_escapes_zero_width_joiner(self):
        """U+200D (Zero Width Joiner) should be escaped."""
        result = _sanitize_text("Hello\u200dWorld")
        assert result == r"Hello\u200dWorld"
        assert "\u200d" not in result

    def test_sanitize_text_escapes_bom_feff(self):
        """U+FEFF (BOM / Zero Width No-Break Space) should be escaped."""
        result = _sanitize_text("Hello\ufeffWorld")
        assert result == r"Hello\ufeffWorld"
        assert "\ufeff" not in result

    def test_sanitize_text_escapes_word_joiner(self):
        """U+2060 (Word Joiner) should be escaped."""
        result = _sanitize_text("Hello\u2060World")
        assert result == r"Hello\u2060World"
        assert "\u2060" not in result


class TestBiDiEdgeCases:
    """Edge cases for BiDi sanitization."""

    def test_multiple_bidi_chars_in_sequence(self):
        """Multiple BiDi chars in sequence should all be escaped."""
        result = _sanitize_text("\u202a\u202b\u202c\u202d\u202e")
        assert "\\u202a" in result
        assert "\\u202b" in result
        assert "\\u202c" in result
        assert "\\u202d" in result
        assert "\\u202e" in result

    def test_just_bidi_char(self):
        """Just a BiDi character should be fully escaped."""
        result = _sanitize_text("\u202e")
        assert result == r"\u202e"
        assert "\u202e" not in result

    def test_normal_unicode_not_affected(self):
        """Normal Unicode characters should not be affected."""
        # These should pass through unchanged
        assert _sanitize_text("こんにちは") == "こんにちは"
        assert _sanitize_text("café") == "café"
        assert _sanitize_text("🎉") == "🎉"
