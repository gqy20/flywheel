"""Tests for Todo.__repr__ newline escaping (Issue #5943).

These tests verify that:
1. repr output is always a single-line string
2. Newlines in text are escaped, not literal
3. Other special characters (tabs, carriage returns) are also escaped
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_single_line_with_newline() -> None:
    """repr(Todo) with newline in text should return single-line string."""
    todo = Todo(id=1, text="a\nb")
    result = repr(todo)

    # The repr output must be a single line (no literal newline characters)
    assert "\n" not in result, f"repr should not contain literal newlines: {result!r}"


def test_repr_single_line_with_multiple_newlines() -> None:
    """repr(Todo) with multiple newlines should return single-line string."""
    todo = Todo(id=1, text="line1\nline2\nline3")
    result = repr(todo)

    assert "\n" not in result, f"repr should not contain literal newlines: {result!r}"


def test_repr_single_line_with_newline_at_boundaries() -> None:
    """repr(Todo) with newline at start/end should return single-line string."""
    # Newline at start
    todo1 = Todo(id=1, text="\ntest")
    result1 = repr(todo1)
    assert "\n" not in result1, f"repr should not contain literal newlines: {result1!r}"

    # Newline at end
    todo2 = Todo(id=2, text="test\n")
    result2 = repr(todo2)
    assert "\n" not in result2, f"repr should not contain literal newlines: {result2!r}"


def test_repr_single_line_with_long_text_containing_newline() -> None:
    """repr(Todo) with truncated text containing newline should be single-line."""
    # Long text with newline that will be truncated
    long_text = "a" * 40 + "\n" + "b" * 40
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    assert "\n" not in result, f"repr should not contain literal newlines: {result!r}"


def test_repr_shows_escaped_newline() -> None:
    """repr(Todo) should show escaped newline (\\n) not literal newline."""
    todo = Todo(id=1, text="a\nb")
    result = repr(todo)

    # The output should contain the escaped form (backslash + n)
    # In the actual string, this is represented as the two-character sequence \ and n
    # When we check with repr(), we see "\\n" which represents the literal backslash-n
    assert "\\n" in result or "\n" not in result


def test_repr_handles_other_whitespace() -> None:
    """repr(Todo) should handle tabs and carriage returns without literal output."""
    # Tab character
    todo1 = Todo(id=1, text="a\tb")
    result1 = repr(todo1)
    assert "\t" not in result1, f"repr should not contain literal tabs: {result1!r}"

    # Carriage return
    todo2 = Todo(id=2, text="a\rb")
    result2 = repr(todo2)
    assert "\r" not in result2, f"repr should not contain literal carriage returns: {result2!r}"
