"""Regression tests for Issue #2316: Unicode control character sanitization.

This test file ensures that Unicode control characters that could affect
terminal display are properly escaped to prevent text spoofing attacks.

The vulnerability occurs when Unicode bidirectional override characters
and zero-width characters are not escaped, allowing attackers to manipulate
text display for spoofing purposes.

Key Unicode control characters to escape:
- U+202A-U+202E: Bidirectional text overrides (LRE, RLE, PDF, LRO, RLO)
- U+200B-U+200D: Zero-width characters (space, non-joiner, joiner)
- U+2066-U+2069: Bidirectional isolation controls
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestUnicodeControlSanitization:
    """Test that Unicode control characters affecting terminal display are escaped."""

    def test_rtl_override_u202e_is_escaped(self):
        """RTL override (U+202E) should be escaped to prevent text spoofing."""
        # U+202E RIGHT-TO-LEFT OVERRIDE
        result = _sanitize_text("test\u202espoof")
        assert result == r"test\u202espoof", (
            f"RTL override should be escaped, got {result!r}"
        )

    def test_ltr_override_u202a_is_escaped(self):
        """LTR override (U+202A) should be escaped."""
        # U+202A LEFT-TO-RIGHT OVERRIDE
        result = _sanitize_text("normal\u202atext")
        assert result == r"normal\u202atext", (
            f"LTR override should be escaped, got {result!r}"
        )

    def test_all_bidi_overrides_escaped(self):
        """All bidirectional override characters (U+202A-U+202E) should be escaped."""
        # U+202A LEFT-TO-RIGHT OVERRIDE
        # U+202B RIGHT-TO-LEFT OVERRIDE
        # U+202C POP DIRECTIONAL FORMAT
        # U+202D LEFT-TO-RIGHT OVERRIDE
        # U+202E RIGHT-TO-LEFT OVERRIDE
        test_cases = [
            ("\u202a", r"\u202a"),  # LRE
            ("\u202b", r"\u202b"),  # RLE
            ("\u202c", r"\u202c"),  # PDF
            ("\u202d", r"\u202d"),  # LRO
            ("\u202e", r"\u202e"),  # RLO
        ]
        for char, expected in test_cases:
            result = _sanitize_text(char)
            assert result == expected, f"Expected {expected!r} for {char!r}, got {result!r}"

    def test_zero_width_space_u200b_is_escaped(self):
        """Zero-width space (U+200B) should be escaped."""
        result = _sanitize_text("before\u200bafter")
        assert result == r"before\u200bafter", (
            f"Zero-width space should be escaped, got {result!r}"
        )

    def test_zero_width_joiners_escaped(self):
        """Zero-width joiner (U+200D) and non-joiner (U+200C) should be escaped."""
        # U+200C ZERO WIDTH NON-JOINER
        result = _sanitize_text("text\u200cmore")
        assert result == r"text\u200cmore"

        # U+200D ZERO WIDTH JOINER
        result = _sanitize_text("text\u200dmore")
        assert result == r"text\u200dmore"

    def test_all_zero_width_chars_escaped(self):
        """All zero-width characters (U+200B-U+200D) should be escaped."""
        test_cases = [
            ("\u200b", r"\u200b"),  # Zero Width Space
            ("\u200c", r"\u200c"),  # Zero Width Non-Joiner
            ("\u200d", r"\u200d"),  # Zero Width Joiner
        ]
        for char, expected in test_cases:
            result = _sanitize_text(char)
            assert result == expected, f"Expected {expected!r} for {char!r}, got {result!r}"

    def test_bidi_isolation_controls_escaped(self):
        """Bidirectional isolation controls (U+2066-U+2069) should be escaped."""
        test_cases = [
            ("\u2066", r"\u2066"),  # LRI
            ("\u2067", r"\u2067"),  # RLI
            ("\u2068", r"\u2068"),  # FSI
            ("\u2069", r"\u2069"),  # PDI
        ]
        for char, expected in test_cases:
            result = _sanitize_text(char)
            assert result == expected, f"Expected {expected!r} for {char!r}, got {result!r}"

    def test_normal_arabic_text_not_escaped(self):
        """Normal Arabic/Hebrew text should NOT be escaped - only control chars."""
        # Arabic text (should pass through unchanged)
        result = _sanitize_text("مرحبا")
        assert result == "مرحبا", f"Normal Arabic text should not be escaped, got {result!r}"

        # Hebrew text (should pass through unchanged)
        result = _sanitize_text("שלום")
        assert result == "שלום", f"Normal Hebrew text should not be escaped, got {result!r}"

    def test_unicode_control_with_ascii_controls(self):
        """Unicode control chars should be escaped alongside ASCII control chars."""
        # Mix of ASCII control, Unicode bidi override, and normal text
        result = _sanitize_text("normal\u202e\x1b[31m")
        assert result == r"normal\u202e\x1b[31m"

    def test_text_spoofing_attack_prevented(self):
        """Test that text spoofing attacks using bidi overrides are prevented."""
        # Attack: display "exe" but actually run "com"
        # Uses U+202E to reverse the display of "exe.mp3"
        malicious = "file\u202exe.mp3.txt"
        result = _sanitize_text(malicious)
        # The RTL override should be escaped, making the attack visible
        assert result == r"file\u202exe.mp3.txt"

    def test_format_todo_with_unicode_control_chars(self):
        """TodoFormatter should properly escape Unicode control characters."""
        todo = Todo(id=1, text="Buy milk\u202e", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy milk\u202e"

    def test_multiple_unicode_controls_consecutive(self):
        """Multiple consecutive Unicode control chars should all be escaped."""
        result = _sanitize_text("test\u202b\u202d\u202eend")
        assert result == r"test\u202b\u202d\u202eend"

    def test_empty_string_and_edge_cases(self):
        """Edge cases should be handled correctly."""
        assert _sanitize_text("") == ""
        # Only Unicode control char
        assert _sanitize_text("\u202e") == r"\u202e"
        # Multiple zero-width spaces
        assert _sanitize_text("\u200b\u200b\u200b") == r"\u200b\u200b\u200b"
