"""Tests for Todo.__repr__ sanitization (Issue #6213).

These tests verify that:
1. Todo.__repr__() output is single-line for any input text
2. Control characters (\\n, \\r, \\t, ANSI codes) in text are escaped in repr output
3. repr output does not contain literal newline characters
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_is_single_line_with_newlines() -> None:
    """repr(Todo) should be single-line even when text contains newlines."""
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)

    # repr output should not contain literal newline characters
    assert "\n" not in result, f"repr should be single-line but got: {result!r}"
    assert "\r" not in result, f"repr should be single-line but got: {result!r}"


def test_repr_escapes_carriage_return() -> None:
    """repr(Todo) should escape carriage return characters."""
    todo = Todo(id=1, text="text\rwith\rcarriage")
    result = repr(todo)

    # repr output should not contain literal carriage return characters
    assert "\r" not in result, f"repr should escape \\r but got: {result!r}"


def test_repr_escapes_tab() -> None:
    """repr(Todo) should escape tab characters."""
    todo = Todo(id=1, text="text\twith\ttabs")
    result = repr(todo)

    # repr output should not contain literal tab characters
    assert "\t" not in result, f"repr should escape \\t but got: {result!r}"


def test_repr_escapes_ansi_escape_codes() -> None:
    """repr(Todo) should escape ANSI escape codes to prevent log injection."""
    # ANSI escape code (e.g., \x1b[31m for red color)
    todo = Todo(id=1, text="normal\x1b[31mred\x1b[0mnormal")
    result = repr(todo)

    # repr output should not contain literal escape character
    assert "\x1b" not in result, f"repr should escape ANSI codes but got: {result!r}"
    # Should contain escaped representation
    assert "\\x1b" in result or "x1b" in result, f"repr should show escaped ANSI but got: {result!r}"


def test_repr_escapes_null_byte() -> None:
    """repr(Todo) should escape null bytes."""
    todo = Todo(id=1, text="text\x00with\x00nulls")
    result = repr(todo)

    # repr output should not contain literal null characters
    assert "\x00" not in result, f"repr should escape \\x00 but got: {result!r}"


def test_repr_escapes_control_characters() -> None:
    """repr(Todo) should escape other control characters (0x01-0x1f)."""
    # Bell character (0x07)
    todo = Todo(id=1, text="text\x07bell")
    result = repr(todo)

    assert "\x07" not in result, f"repr should escape \\x07 but got: {result!r}"


def test_repr_with_mixed_special_characters() -> None:
    """repr(Todo) should handle mixed special characters."""
    todo = Todo(id=1, text="line1\nline2\ttab\x1b[31mcolor\x1b[0m")
    result = repr(todo)

    # Should be single line
    assert "\n" not in result
    assert "\r" not in result
    assert "\t" not in result
    assert "\x1b" not in result


def test_repr_sanitization_preserves_content_info() -> None:
    """repr(Todo) sanitization should still show readable content."""
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)

    # Should still show the id and indicate text content
    assert "id=1" in result
    assert "Todo" in result
    # The escaped newline representation should be present
    assert "\\n" in result or "line" in result
