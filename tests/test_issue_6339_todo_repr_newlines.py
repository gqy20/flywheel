"""Tests for Todo.__repr__ escaping newlines (Issue #6339).

These tests verify that:
1. repr(Todo) does not contain literal newlines in output
2. repr output remains on a single line
3. Control characters are properly escaped
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_repr_no_literal_newline_in_text() -> None:
    """repr(Todo) should not contain literal newlines in the text portion."""
    todo = Todo(id=1, text="a\nb")
    result = repr(todo)

    # The repr output should NOT contain a literal newline character
    # The newline should be escaped as \n (two characters: backslash and n)
    assert "\n" not in result, (
        f"repr should not contain literal newline: {result!r}"
    )


def test_todo_repr_remains_single_line() -> None:
    """repr(Todo) output should remain on a single line."""
    todo = Todo(id=1, text="line1\nline2\nline3")
    result = repr(todo)

    # Count actual newline characters in the output
    newline_count = result.count("\n")

    assert newline_count == 0, (
        f"repr should be single line but has {newline_count} newlines: {result!r}"
    )


def test_todo_repr_escapes_various_control_characters() -> None:
    """repr(Todo) should escape various control characters."""
    test_cases = [
        ("\n", "newline"),
        ("\r", "carriage return"),
        ("\t", "tab"),
        ("\x00", "null byte"),
        ("\x1b", "escape"),
    ]

    for char, desc in test_cases:
        text = f"a{char}b"
        todo = Todo(id=1, text=text)
        result = repr(todo)

        # The repr should not contain the literal control character
        assert char not in result, (
            f"repr should escape {desc}: got {result!r}"
        )


def test_todo_repr_with_truncated_text_containing_newline() -> None:
    """repr(Todo) should escape newlines even in truncated text."""
    # Create text long enough to trigger truncation, with newline near the start
    long_text = "start\n" + "x" * 50
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # Should not contain literal newline
    assert "\n" not in result, (
        f"repr should escape newline in truncated text: {result!r}"
    )
    # Should contain truncation indicator
    assert "..." in result


def test_todo_repr_with_multiple_newlines() -> None:
    """repr(Todo) should handle text with multiple newlines."""
    todo = Todo(id=1, text="\n\n\n\n\n")
    result = repr(todo)

    # Should not contain any literal newlines
    assert "\n" not in result, (
        f"repr should escape all newlines: {result!r}"
    )
