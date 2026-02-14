"""Tests for Todo.__repr__ truncation with newline handling (Issue #3296).

This test verifies that when text is truncated AND contains newlines,
the repr output does not contain literal newline characters.

The issue: __repr__ truncates text at 47 chars, but if the truncated
portion contains a newline, the !r format specifier should escape it
to \\n (two characters), not leave it as a literal newline.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_truncated_text_with_newline_no_literal_newline() -> None:
    """repr(Todo) with long text containing newline should not have literal newlines.

    This tests the exact acceptance criteria from issue #3296:
    - text = 'a'*40 + '\\n' + 'b'*20 (length 61, contains newline at position 40)
    - repr output should be a single line (no literal newline characters)
    """
    # Create text that is > 50 chars AND contains a newline
    text = "a" * 40 + "\n" + "b" * 20  # 61 chars, newline at position 40
    todo = Todo(id=1, text=text)

    result = repr(todo)

    # Core assertion: no literal newline in the repr output
    assert "\n" not in result, (
        f"repr should not contain literal newline: {result!r}"
    )

    # The output should be a single line
    assert len(result.splitlines()) == 1, (
        f"repr should be single line, got {len(result.splitlines())} lines: {result!r}"
    )


def test_repr_truncated_text_newline_near_truncation_point() -> None:
    """repr(Todo) should handle newline near the 47-char truncation boundary."""
    # Newline at position 46 (within truncation range)
    text = "a" * 46 + "\n" + "b" * 10  # 57 chars
    todo = Todo(id=1, text=text)

    result = repr(todo)

    assert "\n" not in result, f"repr should escape newline: {result!r}"
    assert len(result.splitlines()) == 1


def test_repr_truncated_text_multiple_newlines() -> None:
    """repr(Todo) should handle multiple newlines in truncated text."""
    # Multiple newlines within truncation range
    text = "line1\n" * 10 + "more text here"  # > 50 chars with multiple newlines
    todo = Todo(id=1, text=text)

    result = repr(todo)

    # Should have no literal newlines (all escaped to \\n)
    literal_newlines = result.count("\n")
    assert literal_newlines == 0, (
        f"repr should have 0 literal newlines, got {literal_newlines}: {result!r}"
    )
    assert len(result.splitlines()) == 1
