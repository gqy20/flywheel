"""Regression tests for Issue #3846: Bidirectional text control character sanitization.

Bidirectional text control characters (U+202A-U+202E) and zero-width characters
(U+200B-U+200F, U+2060, U+FEFF) can be used for visual spoofing attacks,
including Trojan Source attacks that reorder displayed text to hide malicious content.

These should be sanitized to prevent such attacks.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidirectionalControlSanitization:
    """Test that bidirectional text control characters are properly escaped."""

    def test_sanitize_text_escapes_rlo_character(self):
        """Right-to-Left Override (U+202E) should be escaped."""
        # RLO can reverse text display, hiding malicious content
        result = _sanitize_text("Hello\u202eEvil")
        assert "\\u202e" in result
        assert "\u202e" not in result

    def test_sanitize_text_escapes_lro_character(self):
        """Left-to-Right Override (U+202D) should be escaped."""
        result = _sanitize_text("Text\u202dNormal")
        assert "\\u202d" in result
        assert "\u202d" not in result

    def test_sanitize_text_escapes_all_bidi_overrides(self):
        """All bidirectional override characters should be escaped."""
        # LRE (U+202A), RLE (U+202B), PDF (U+202C), LRO (U+202D), RLO (U+202E)
        bidi_chars = ["\u202a", "\u202b", "\u202c", "\u202d", "\u202e"]
        for char in bidi_chars:
            result = _sanitize_text(f"before{char}after")
            assert char not in result, f"Character U+{ord(char):04X} was not escaped"
            assert f"\\u{ord(char):04x}" in result, f"Character U+{ord(char):04X} not properly escaped"

    def test_sanitize_text_escapes_zero_width_space(self):
        """Zero-width space (U+200B) should be escaped."""
        result = _sanitize_text("Visible\u200bHidden")
        assert "\\u200b" in result
        assert "\u200b" not in result

    def test_sanitize_text_escapes_zero_width_joiner(self):
        """Zero-width joiner (U+200D) should be escaped."""
        result = _sanitize_text("A\u200dB")
        assert "\\u200d" in result
        assert "\u200d" not in result

    def test_sanitize_text_escapes_zero_width_non_joiner(self):
        """Zero-width non-joiner (U+200C) should be escaped."""
        result = _sanitize_text("A\u200cB")
        assert "\\u200c" in result
        assert "\u200c" not in result

    def test_sanitize_text_escapes_direction_marks(self):
        """Left-to-Right Mark (U+200E) and Right-to-Left Mark (U+200F) should be escaped."""
        # LRM
        result_lrm = _sanitize_text("Text\u200eMore")
        assert "\\u200e" in result_lrm
        assert "\u200e" not in result_lrm
        # RLM
        result_rlm = _sanitize_text("Text\u200fMore")
        assert "\\u200f" in result_rlm
        assert "\u200f" not in result_rlm

    def test_sanitize_text_escapes_word_joiner(self):
        """Word joiner (U+2060) should be escaped."""
        result = _sanitize_text("word\u2060join")
        assert "\\u2060" in result
        assert "\u2060" not in result

    def test_sanitize_text_escapes_bom(self):
        """Byte Order Mark / Zero-width no-break space (U+FEFF) should be escaped."""
        result = _sanitize_text("\ufeffText")
        assert "\\ufeff" in result
        assert "\ufeff" not in result

    def test_sanitize_text_bidi_attack_example(self):
        """Test a realistic Trojan Source attack pattern."""
        # This would display as "Good" in some contexts but contains hidden "Evil"
        # RLO reverses the display of following characters
        result = _sanitize_text("Good\u202eEvil\u202c")
        # Both characters should be escaped
        assert "\\u202e" in result
        assert "\\u202c" in result
        assert "\u202e" not in result
        assert "\u202c" not in result

    def test_format_todo_escapes_bidi_chars(self):
        """Todo with bidi chars should output escaped representation."""
        todo = Todo(id=1, text="Clean room\u202eFAKE_TODO\u202c", done=False)
        result = TodoFormatter.format_todo(todo)
        # Should contain escaped representation
        assert "\\u202e" in result
        assert "\\u202c" in result
        # Should not contain actual bidi characters
        assert "\u202e" not in result
        assert "\u202c" not in result


class TestZeroWidthFullRange:
    """Test the full range of zero-width and formatting characters."""

    def test_sanitize_text_zero_width_chars_full_range(self):
        """Test all zero-width characters in the U+200B-U+200F range."""
        zw_chars = {
            "\u200b": "Zero-width space",
            "\u200c": "Zero-width non-joiner",
            "\u200d": "Zero-width joiner",
            "\u200e": "Left-to-Right Mark",
            "\u200f": "Right-to-Left Mark",
        }
        for char, name in zw_chars.items():
            result = _sanitize_text(f"test{char}case")
            assert char not in result, f"{name} (U+{ord(char):04X}) was not escaped"
            assert f"\\u{ord(char):04x}" in result

    def test_valid_unicode_not_affected(self):
        """Valid Unicode characters should not be affected."""
        # These should pass through unchanged
        assert _sanitize_text("Hello World") == "Hello World"
        assert _sanitize_text("café") == "café"
        assert _sanitize_text("日本語") == "日本語"
        assert _sanitize_text("🎉") == "🎉"
