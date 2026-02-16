"""Tests for Todo.__repr__ single-line guarantee (Issue #3663).

This test ensures that repr(Todo) always produces single-line output,
even when the text contains newline characters or other control characters.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_repr_no_literal_newline() -> None:
    """repr(Todo) must not contain literal newline characters."""
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)

    # Strict check: no literal newline character (ord=10) in output
    assert "\n" not in result, f"repr contains literal newline: {result!r}"


def test_todo_repr_no_literal_carriage_return() -> None:
    """repr(Todo) must not contain literal carriage return characters."""
    todo = Todo(id=1, text="line1\rline2")
    result = repr(todo)

    # Strict check: no literal CR character (ord=13) in output
    assert "\r" not in result, f"repr contains literal CR: {result!r}"


def test_todo_repr_single_line_with_multiple_newlines() -> None:
    """repr(Todo) must be a single line even with multiple newlines in text."""
    todo = Todo(id=1, text="line1\nline2\nline3\nline4")
    result = repr(todo)

    # Count lines by splitting on literal newlines
    lines = result.split("\n")
    assert len(lines) == 1, f"repr has {len(lines)} lines: {result!r}"


def test_todo_repr_control_chars_escaped() -> None:
    """repr(Todo) should escape control characters properly."""
    # Test various control characters
    test_cases = [
        ("\n", "newline"),
        ("\r", "carriage return"),
        ("\t", "tab"),
        ("\x00", "null"),
        ("\x07", "bell"),
        ("\x1b", "escape"),
    ]

    for char, name in test_cases:
        todo = Todo(id=1, text=f"before{char}after")
        result = repr(todo)

        # Check no literal control character in output
        assert char not in result, f"repr contains literal {name} ({ord(char)}): {result!r}"


def test_todo_repr_length_under_100_chars() -> None:
    """repr(Todo) output must remain under 100 characters for normal todos."""
    # Normal todo with newline
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)

    assert len(result) < 100, f"repr too long ({len(result)} chars): {result!r}"
