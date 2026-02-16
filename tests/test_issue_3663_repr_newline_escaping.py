"""Tests for Todo.__repr__ newline escaping (Issue #3663).

These tests verify that:
1. repr(Todo) output is always single-line (no literal newline characters)
2. repr output remains under 100 characters for normal todos
3. All control characters are properly escaped
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_single_line_with_newline_in_text() -> None:
    """repr(Todo) must output a single line even when text contains newlines."""
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)

    # The output must NOT contain any literal newline characters
    # This ensures single-line output in debuggers/logs
    assert "\n" not in result, (
        f"repr output contains literal newline: {result!r}"
    )
    assert "\r" not in result, (
        f"repr output contains literal carriage return: {result!r}"
    )


def test_repr_single_line_with_truncated_text_containing_newline() -> None:
    """repr(Todo) must remain single-line when truncated text contains newlines."""
    # Create text longer than 50 chars with embedded newlines
    long_text_with_newlines = "a" * 25 + "\n" + "b" * 50
    todo = Todo(id=1, text=long_text_with_newlines)
    result = repr(todo)

    # After truncation, should still be single-line
    assert "\n" not in result, (
        f"repr output contains literal newline after truncation: {result!r}"
    )


def test_repr_single_line_with_multiple_control_chars() -> None:
    """repr(Todo) must escape all control characters to maintain single-line output."""
    text_with_controls = "line1\nline2\r\nline3\ttab"
    todo = Todo(id=1, text=text_with_controls)
    result = repr(todo)

    # None of these should appear as literal characters
    assert "\n" not in result
    assert "\r" not in result
    assert "\t" not in result


def test_repr_concise_for_normal_todos() -> None:
    """repr(Todo) output should remain under 100 characters for normal todos."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = repr(todo)

    assert len(result) < 100, f"repr too long: {len(result)} chars - {result}"
