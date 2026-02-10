"""Regression test for Issue #2726: Verify no collision between literal r'\n' and actual newline.

This test confirms that the fix for Issue #2097 correctly handles the case where
literal backslash-n text (r'\n') is distinguishable from actual newline character ('\n').

Issue #2726 was raised as a false positive - the current implementation is correct.
"""

from __future__ import annotations

from flywheel.formatter import _sanitize_text


class TestIssue2726LiteralNewlineCollision:
    """Verify no collision exists between literal r'\n' and actual newline."""

    def test_literal_backslash_n_vs_actual_newline_no_collision(self):
        """Literal r'\n' and actual newline produce different outputs.

        The fix for Issue #2097 escapes backslash BEFORE replacing control characters.
        This means:
        1. Input r'\n' (literal: backslash + n) → backslash becomes \\ → r'\\n'
        2. Input '\n' (actual newline) → replaced with \\n → r'\n'

        Result: r'\\n' (3 chars) vs r'\n' (2 chars) - NO COLLISION
        """
        # Literal text: backslash followed by 'n'
        literal_input = r"\n"
        literal_output = _sanitize_text(literal_input)

        # Actual newline character
        actual_input = "\n"
        actual_output = _sanitize_text(actual_input)

        # Verify outputs are DIFFERENT (no collision)
        assert literal_output != actual_output, (
            "COLLISION DETECTED: Literal r'\\n' and actual newline "
            "produced identical output!"
        )

        # Verify actual newline produces r'\n' (2 characters)
        assert actual_output == r"\n", (
            f"Actual newline should escape to r'\\n' (2 chars), got {actual_output!r}"
        )
        assert len(actual_output) == 2, (
            f"Actual newline output should be 2 chars, got {len(actual_output)}"
        )

        # Verify literal text produces r'\\n' (3 characters: escaped backslash + n)
        assert literal_output == r"\\n", (
            f"Literal r'\\n' should escape to r'\\\\n' (3 chars), got {literal_output!r}"
        )
        assert len(literal_output) == 3, (
            f"Literal text output should be 3 chars, got {len(literal_output)}"
        )

    def test_literal_backslash_x_vs_actual_control_char_no_collision(self):
        """Literal r'\x01' and actual control char produce different outputs."""
        # Literal text: backslash, x, 0, 1
        literal_input = r"\x01"
        literal_output = _sanitize_text(literal_input)

        # Actual SOH control character
        actual_input = "\x01"
        actual_output = _sanitize_text(actual_input)

        # Verify outputs are DIFFERENT
        assert literal_output != actual_output, (
            "COLLISION DETECTED: Literal r'\\x01' and actual control char "
            "produced identical output!"
        )

        # Actual control char should be r'\x01' (4 chars)
        assert actual_output == r"\x01"
        assert len(actual_output) == 4

        # Literal text should be r'\\x01' (5 chars: escaped backslash + x01)
        assert literal_output == r"\\x01"
        assert len(literal_output) == 5

    def test_all_escape_sequences_distinguishable_from_literals(self):
        """Comprehensive test: all escape sequences distinguishable from literals."""
        test_cases = [
            ("\n", r"\n", "newline"),
            ("\r", r"\r", "carriage return"),
            ("\t", r"\t", "tab"),
            ("\x00", r"\x00", "null"),
            ("\x1b", r"\x1b", "escape"),
            ("\x7f", r"\x7f", "DEL"),
        ]

        for control_char, escaped_repr, name in test_cases:
            # Test actual control character
            control_output = _sanitize_text(control_char)

            # Test literal escape sequence text
            literal_output = _sanitize_text(escaped_repr)

            # Must be distinguishable
            assert control_output != literal_output, (
                f"COLLISION: Actual {name} and literal r'{escaped_repr}' "
                f"both produce {control_output!r}"
            )

            # Control char output should be the escaped representation
            assert control_output == escaped_repr, (
                f"Control {name} should escape to {escaped_repr!r}, got {control_output!r}"
            )

            # Literal output should have an extra backslash
            expected_literal = "\\" + escaped_repr
            assert literal_output == expected_literal, (
                f"Literal r'{escaped_repr}' should escape to {expected_literal!r}, "
                f"got {literal_output!r}"
            )
