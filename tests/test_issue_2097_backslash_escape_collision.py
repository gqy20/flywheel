"""Regression tests for Issue #2097: Backslash escape collision.

This test file ensures that literal backslash escape sequences (like \n, \t typed
by the user) are distinguishable from actual control characters after sanitization.

The bug: When a user types literal "\n" (backslash + n), it looks the same as
an actual newline character after sanitization, creating an ambiguity/collision.
"""

from __future__ import annotations

from flywheel.formatter import _sanitize_text


class TestBackslashEscapeCollision:
    """Test that literal backslash escapes are distinguishable from control characters."""

    def test_literal_backslash_n_vs_actual_newline_different(self):
        """Literal backslash-n should be distinguishable from actual newline.

        When user types the two characters '\' and 'n', it should be escaped
        differently from an actual control newline character (0x0a).
        """
        # Actual newline character (single character, 0x0a)
        actual_newline = "Hello\nWorld"
        result_newline = _sanitize_text(actual_newline)

        # Literal backslash-n (two characters: backslash and 'n')
        literal_backslash_n = "Hello\\nWorld"
        result_literal = _sanitize_text(literal_backslash_n)

        # These should produce DIFFERENT outputs to avoid ambiguity
        assert result_newline != result_literal, (
            "Actual newline and literal \\n must produce different outputs"
        )

        # Actual newline should be escaped as \\n
        assert result_newline == r"Hello\nWorld"

        # Literal backslash-n should have the backslash escaped, producing \\\\n
        # so that when displayed, the user can tell the difference
        assert result_literal == r"Hello\\nWorld"

    def test_literal_backslash_t_vs_actual_tab_different(self):
        """Literal backslash-t should be distinguishable from actual tab."""
        # Actual tab character
        actual_tab = "Hello\tWorld"
        result_tab = _sanitize_text(actual_tab)

        # Literal backslash-t (two characters)
        literal_backslash_t = "Hello\\tWorld"
        result_literal = _sanitize_text(literal_backslash_t)

        # These should produce DIFFERENT outputs
        assert result_tab != result_literal, (
            "Actual tab and literal \\t must produce different outputs"
        )

        # Actual tab should be escaped as \\t
        assert result_tab == r"Hello\tWorld"

        # Literal backslash-t should have the backslash escaped
        assert result_literal == r"Hello\\tWorld"

    def test_literal_backslash_r_vs_actual_carriage_return_different(self):
        """Literal backslash-r should be distinguishable from actual carriage return."""
        # Actual carriage return
        actual_cr = "Hello\rWorld"
        result_cr = _sanitize_text(actual_cr)

        # Literal backslash-r (two characters)
        literal_backslash_r = "Hello\\rWorld"
        result_literal = _sanitize_text(literal_backslash_r)

        # These should produce DIFFERENT outputs
        assert result_cr != result_literal, (
            "Actual carriage return and literal \\r must produce different outputs"
        )

        # Actual CR should be escaped as \\r
        assert result_cr == r"Hello\rWorld"

        # Literal backslash-r should have the backslash escaped
        assert result_literal == r"Hello\\rWorld"

    def test_backslash_properly_escaped(self):
        """Lone backslash character should be escaped."""
        # Single backslash (not followed by n, t, r)
        lone_backslash = "path\\to\\file"
        result = _sanitize_text(lone_backslash)

        # Backslash should be escaped
        assert result == r"path\\to\\file"

    def test_mixed_backslash_and_control_chars(self):
        """Test text with both literal backslashes and actual control characters."""
        # Text with both literal backslash and actual newline
        mixed = "item\\n\nitem"
        result = _sanitize_text(mixed)

        # Should escape both: literal backslash becomes \\, actual newline becomes \n
        # So "item\\n" (item + literal backslash + n) becomes "item\\\\n"
        # And "\n" (actual newline) becomes "\n"
        # Result: "item\\\\n\nitem"
        assert result == r"item\\n\nitem"

    def test_backslash_x_collision(self):
        """Test literal backslash-x sequences don't collide with hex escapes."""
        # Literal \x01 (4 characters: backslash, x, 0, 1)
        literal_hex = "text\\x01"
        result_literal = _sanitize_text(literal_hex)

        # Actual control character 0x01 (SOH - Start of Heading)
        actual_ctrl = "text\x01"
        result_ctrl = _sanitize_text(actual_ctrl)

        # Should produce different outputs
        assert result_literal != result_ctrl

        # Actual control char should be \x01
        assert result_ctrl == r"text\x01"

        # Literal backslash-x should have backslash escaped
        assert result_literal == r"text\\x01"

    def test_normal_text_unchanged(self):
        """Normal text without backslashes or control chars should pass through."""
        normal = "Hello World 123"
        result = _sanitize_text(normal)
        assert result == normal
