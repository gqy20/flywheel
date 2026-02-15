"""Tests for Todo.__repr__ control character sanitization (Issue #3489).

These tests verify that:
1. repr(Todo) does not contain literal newline characters
2. repr(Todo) output is always a single line
3. repr(Todo) properly escapes all control characters
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_repr_no_literal_newline() -> None:
    """repr(Todo) should not contain literal newline characters."""
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)

    # Should not have any literal newline characters
    assert "\n" not in result, f"repr should not contain literal newlines: {result!r}"


def test_todo_repr_single_line_output() -> None:
    """repr(Todo) output should always be a single line."""
    todo = Todo(id=1, text="line1\nline2\nline3")
    result = repr(todo)

    # Output should be single line (no newline characters)
    lines = result.split("\n")
    assert len(lines) == 1, f"repr should be single line, got {len(lines)} lines: {result!r}"


def test_todo_repr_escapes_various_control_chars() -> None:
    """repr(Todo) should escape all common control characters."""
    test_cases = [
        ("text\nwith\nnewlines", "newline"),
        ("text\twith\ttabs", "tab"),
        ("text\rwith\rcarriage", "carriage return"),
        ("text\x00with\x00null", "null byte"),
        ("text\x7fwith\x7fdel", "DEL char"),
    ]

    for text, desc in test_cases:
        todo = Todo(id=1, text=text)
        result = repr(todo)

        # Check no control characters (0x00-0x1f, 0x7f) in output
        for char in result:
            code = ord(char)
            assert not (
                code <= 0x1f or code == 0x7f
            ), f"{desc}: repr contains control char {hex(code)}: {result!r}"


def test_todo_repr_long_text_with_newline() -> None:
    """repr(Todo) should handle truncation with newlines correctly."""
    # Text longer than 50 chars with newline in the middle
    long_text = "This is a long text with a newline\nin the middle"
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # Should still be single line and not contain literal newlines
    assert "\n" not in result, f"repr should not contain literal newlines: {result!r}"
    assert len(result.split("\n")) == 1, f"repr should be single line: {result!r}"


def test_todo_repr_newline_in_first_47_chars() -> None:
    """repr(Todo) should escape newlines even in truncated portion."""
    # Newline in the first 47 chars (the truncated portion)
    text_with_early_newline = "This\nhas an early newline and is quite long"
    todo = Todo(id=1, text=text_with_early_newline)
    result = repr(todo)

    assert "\n" not in result, f"repr should not contain literal newlines: {result!r}"
