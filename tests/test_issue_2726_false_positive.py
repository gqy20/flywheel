"""Regression test for Issue #2726: Verify claimed collision is actually a false positive.

Issue #2726 claims that literal r'\\n' and actual newline both produce r'\\n' output,
creating a collision. This test verifies that the fix for Issue #2097 correctly handles
this case and the claim in #2726 is a false positive.

The test should PASS if the code is correct (no collision exists).
The test should FAIL if there is actually a collision bug.

Expected behavior after fix for Issue #2097:
- Input literal r'\\n' (backslash + n) → r'\\\\n' (3 chars: double backslash + n)
- Input actual newline '\\n' → r'\\n' (2 chars: backslash + n)
- These outputs MUST be different to prevent collision.
"""

from __future__ import annotations

from flywheel.formatter import _sanitize_text


def test_issue_2726_claimed_collision_is_false_positive():
    """Verify the claimed collision in issue #2726 does not actually exist.

    Issue #2726 incorrectly claims that after fixing #2097:
    - Literal r'\\n' (backslash-n as text) and actual newline character
    - Both produce r'\\n' output

    This is FALSE. The correct behavior is:
    - Literal r'\\n' → r'\\\\n' (escaped backslash + n)
    - Actual '\\n' → r'\\n' (escaped newline)

    These are DISTINCT outputs with different lengths (3 vs 2 characters).
    """
    # Test actual newline character (1 char)
    actual_newline_input = "\n"
    actual_newline_output = _sanitize_text(actual_newline_input)

    # Test literal backslash-n text (2 characters: backslash, n)
    literal_newline_input = r"\n"
    literal_newline_output = _sanitize_text(literal_newline_input)

    # These MUST be different - if they're the same, there's a bug
    assert actual_newline_output != literal_newline_output, (
        "BUG CONFIRMED: Actual newline and literal \\n text produced identical output! "
        "The fix for Issue #2097 failed to prevent collision."
    )

    # Verify actual newline produces r'\n' (2 characters)
    assert actual_newline_output == r"\n", (
        f"Expected r'\\n' for actual newline, got {actual_newline_output!r}"
    )
    assert len(actual_newline_output) == 2, (
        f"Actual newline output should be 2 chars, got {len(actual_newline_output)}"
    )

    # Verify literal text produces r'\\n' (3 characters: escaped backslash + n)
    assert literal_newline_output == r"\\n", (
        f"Expected r'\\\\n' for literal \\n, got {literal_newline_output!r}"
    )
    assert len(literal_newline_output) == 3, (
        f"Literal \\n output should be 3 chars, got {len(literal_newline_output)}"
    )

    # Final verification: outputs are distinguishable by both content AND length
    assert len(actual_newline_output) != len(literal_newline_output), (
        "BUG: Outputs have same length - potential collision detected!"
    )


def test_issue_2726_all_escape_sequences_distinguishable():
    """Comprehensive test that all common escape sequences are distinguishable.

    This extends the test from issue #2726's claim to verify that ALL escape
    sequences work correctly, not just \\n.
    """
    # Each tuple: (actual control char, literal text representation, expected escaped output)
    test_cases = [
        ("\n", r"\n", r"\n"),  # newline
        ("\r", r"\r", r"\r"),  # carriage return
        ("\t", r"\t", r"\t"),  # tab
    ]

    for control_char, literal_input, expected_escaped in test_cases:
        # Actual control character produces escaped output
        actual_output = _sanitize_text(control_char)
        assert actual_output == expected_escaped, (
            f"Control char {control_char!r} should escape to {expected_escaped!r}, "
            f"got {actual_output!r}"
        )

        # Literal text (the escaped representation) gets backslash escaped
        literal_output = _sanitize_text(literal_input)

        # Literal should have one more backslash (escaped once more)
        expected_doubled = "\\" + expected_escaped
        assert literal_output == expected_doubled, (
            f"Literal text {literal_input!r} should escape to {expected_doubled!r}, "
            f"got {literal_output!r}"
        )

        # Most importantly: they MUST be different
        assert actual_output != literal_output, (
            f"BUG CONFIRMED: Control char {control_char!r} and literal {literal_input!r} "
            f"produced identical output {actual_output!r}!"
        )
