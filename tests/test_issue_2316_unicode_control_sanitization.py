"""Tests for Unicode control character sanitization (Issue #2316).

Unicode bidirectional override characters (U+202A-U+202E) and zero-width
characters (U+200B-U+200D) can be used for text spoofing attacks where
an attacker can manipulate how text appears in terminals without changing
the actual text content.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestUnicodeBidirectionalOverrideSanitization:
    """Test that Unicode bidirectional override characters are properly escaped."""

    def test_sanitize_text_escapes_rtl_override_u202e(self) -> None:
        """RTL override (U+202E) should be escaped to prevent text spoofing."""
        # U+202E = RIGHT-TO-LEFT OVERRIDE
        result = _sanitize_text("file.txt\u202eexe")
        assert "\\u202e" in result
        assert "\u202e" not in result

    def test_sanitize_text_escapes_ltr_override_u202a(self) -> None:
        """LTR override (U+202A) should be escaped."""
        # U+202A = LEFT-TO-RIGHT OVERRIDE
        result = _sanitize_text("test\u202astring")
        assert "\\u202a" in result
        assert "\u202a" not in result

    def test_sanitize_text_escapes_all_bidi_overrides_u202a_to_u202e(self) -> None:
        """Test full range of bidirectional override characters (U+202A-U+202E)."""
        # U+202A LRE, U+202B RLE, U+202C PDF, U+202D LRO, U+202E RLO
        test_cases = [
            ("\u202a", "\\u202a"),  # LTR override
            ("\u202b", "\\u202b"),  # RTL override
            ("\u202c", "\\u202c"),  # POP DIRECTIONAL FORMATTING
            ("\u202d", "\\u202d"),  # LTR override
            ("\u202e", "\\u202e"),  # RTL override
        ]
        for input_char, expected_escaped in test_cases:
            result = _sanitize_text(input_char)
            assert result == expected_escaped


class TestZeroWidthCharacterSanitization:
    """Test that zero-width characters are properly escaped."""

    def test_sanitize_text_escapes_zero_width_space_u200b(self) -> None:
        """Zero-width space (U+200B) should be escaped."""
        result = _sanitize_text("test\u200bstring")
        assert "\\u200b" in result
        assert "\u200b" not in result

    def test_sanitize_text_escapes_all_zero_width_chars_u200b_to_u200d(self) -> None:
        """Test full range of zero-width characters (U+200B-U+200D)."""
        test_cases = [
            ("\u200b", "\\u200b"),  # ZERO WIDTH SPACE
            ("\u200c", "\\u200c"),  # ZERO WIDTH NON-JOINER
            ("\u200d", "\\u200d"),  # ZERO WIDTH JOINER
        ]
        for input_char, expected_escaped in test_cases:
            result = _sanitize_text(input_char)
            assert result == expected_escaped


class TestValidUnicodeTextPassThrough:
    """Ensure legitimate Unicode text is NOT affected by sanitization."""

    def test_normal_arabic_text_not_escaped(self) -> None:
        """Normal Arabic text should NOT be escaped - it's legitimate content."""
        # Arabic text for "Hello"
        arabic_text = "مرحبا"
        result = _sanitize_text(arabic_text)
        assert result == arabic_text

    def test_normal_hebrew_text_not_escaped(self) -> None:
        """Normal Hebrew text should NOT be escaped."""
        # Hebrew text for "Shalom"
        hebrew_text = "שלום"
        result = _sanitize_text(hebrew_text)
        assert result == hebrew_text

    def test_normal_emoji_not_escaped(self) -> None:
        """Emoji and other legitimate Unicode should pass through."""
        assert _sanitize_text("🎉") == "🎉"
        assert _sanitize_text(" café ") == " café "


class TestFormatTodoWithUnicodeControlChars:
    """Integration tests with TodoFormatter."""

    def test_format_todo_escapes_rtl_override_attack(self) -> None:
        """Test a realistic text spoofing attack scenario."""
        # Attacker creates: "file.txt" + RTL_OVERRIDE + "exe"
        # This displays as "fileexe.txt" but actual content is "file.txtexe"
        todo = Todo(id=1, text="report.doc\u202eexe", done=False)
        result = TodoFormatter.format_todo(todo)
        assert "\\u202e" in result
        assert "\u202e" not in result

    def test_format_todo_with_zero_width_spoofing(self) -> None:
        """Test zero-width character attack in todo."""
        todo = Todo(id=1, text="safe\u200bmalicious", done=False)
        result = TodoFormatter.format_todo(todo)
        assert "\\u200b" in result
        assert "\u200b" not in result
