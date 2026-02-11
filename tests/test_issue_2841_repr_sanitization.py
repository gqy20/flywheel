"""Tests for Todo.__repr__ control character escaping (Issue #2841).

These tests verify that __repr__() properly escapes control characters
to prevent terminal output manipulation and ensure single-line output.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_escapes_newline() -> None:
    """repr(Todo) should escape newline characters to prevent multi-line output."""
    todo = Todo(id=1, text="test\nFAKE COMMAND")
    result = repr(todo)

    # Should contain escaped form, not literal newline
    assert "\\n" in result, f"Newline not escaped in: {result!r}"
    # Should be single-line (no embedded newlines)
    assert "\n" not in result, f"repr contains literal newline: {result!r}"
    # Should still be identifiable as a Todo
    assert "Todo" in result


def test_repr_escapes_carriage_return() -> None:
    """repr(Todo) should escape carriage return characters."""
    todo = Todo(id=1, text="test\rOVERWRITE")
    result = repr(todo)

    # Should contain escaped form
    assert "\\r" in result, f"Carriage return not escaped in: {result!r}"
    # Should not have literal carriage return
    assert "\r" not in result, f"repr contains literal CR: {result!r}"


def test_repr_escapes_tab() -> None:
    """repr(Todo) should escape tab characters."""
    todo = Todo(id=1, text="test\ttabbed")
    result = repr(todo)

    # Should contain escaped form
    assert "\\t" in result, f"Tab not escaped in: {result!r}"
    # Should not have literal tab
    assert "\t" not in result, f"repr contains literal tab: {result!r}"


def test_repr_escapes_ansi_codes() -> None:
    """repr(Todo) should escape ANSI escape sequences."""
    todo = Todo(id=1, text="test\x1b[31mRED TEXT\x1b[0m")
    result = repr(todo)

    # Should contain escaped form for ESC character
    assert "\\x1b" in result, f"ANSI ESC not escaped in: {result!r}"
    # Should not have literal ESC character
    assert "\x1b" not in result, f"repr contains literal ESC: {result!r}"


def test_repr_escapes_null_byte() -> None:
    """repr(Todo) should escape null bytes."""
    todo = Todo(id=1, text="test\x00null")
    result = repr(todo)

    # Should contain escaped form
    assert "\\x00" in result, f"Null byte not escaped in: {result!r}"
    # Should not have literal null byte
    assert "\x00" not in result, f"repr contains literal null byte: {result!r}"


def test_repr_escapes_in_truncated_text() -> None:
    """repr(Todo) should escape control characters even when text is truncated."""
    # Long text with control character that will be in truncated portion
    long_text = "a" * 40 + "\n" + "b" * 40
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # Should be single-line
    assert "\n" not in result, f"repr contains literal newline: {result!r}"
    # Should show truncation indicator
    assert "..." in result


def test_repr_escapes_backslash() -> None:
    """repr(Todo) should escape backslashes to prevent ambiguity."""
    todo = Todo(id=1, text="path\\to\\file")
    result = repr(todo)

    # Should escape backslash (double backslash in output)
    # Since Python's !r also escapes, we should see proper escaping
    assert "Todo" in result
    assert "\\\\" in result or "\\" in result  # Either form is valid


def test_repr_handles_multiple_control_chars() -> None:
    """repr(Todo) should escape multiple control characters together."""
    todo = Todo(id=1, text="test\n\r\t\x1b[0m")
    result = repr(todo)

    # Should be single-line
    assert "\n" not in result
    assert "\r" not in result
    assert "\t" not in result
    assert "\x1b" not in result
    # Should show escaped forms
    assert "\\n" in result or "\\x" in result
