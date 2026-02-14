"""Tests for Todo.__repr__ control character escaping (Issue #3255).

These tests verify that:
1. ANSI escape sequences are sanitized in __repr__
2. Newlines and other control characters are properly escaped
3. __repr__ output is safe to display in terminals
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_repr_escapes_ansi_sequences() -> None:
    """repr(Todo) should not contain actual ANSI escape sequences."""
    # Text with ANSI escape sequence (red color)
    text_with_ansi = "a\x1b[31mRed\x1b[0mb"
    todo = Todo(id=1, text=text_with_ansi)
    result = repr(todo)

    # Should not contain the actual ESC character (0x1b)
    assert "\x1b" not in result, f"repr contains unescaped ESC: {result!r}"

    # Should contain escaped representation like \x1b
    assert "\\x1b" in result, f"repr should have escaped ESC: {result!r}"


def test_todo_repr_escapes_newlines() -> None:
    """repr(Todo) should escape newlines to single-line output."""
    todo = Todo(id=2, text="line1\nline2")
    result = repr(todo)

    # Should not have literal newline in the repr output
    assert "\n" not in result, f"repr contains literal newline: {result!r}"

    # Should have escaped newline representation
    assert "\\n" in result, f"repr should have escaped newline: {result!r}"


def test_todo_repr_escapes_carriage_return() -> None:
    """repr(Todo) should escape carriage return characters."""
    todo = Todo(id=3, text="text\rmore")
    result = repr(todo)

    # Should not have literal CR
    assert "\r" not in result, f"repr contains literal CR: {result!r}"

    # Should have escaped representation
    assert "\\r" in result, f"repr should have escaped CR: {result!r}"


def test_todo_repr_escapes_tab() -> None:
    """repr(Todo) should escape tab characters."""
    todo = Todo(id=4, text="col1\tcol2")
    result = repr(todo)

    # Should not have literal tab
    assert "\t" not in result, f"repr contains literal tab: {result!r}"

    # Should have escaped representation
    assert "\\t" in result, f"repr should have escaped tab: {result!r}"


def test_todo_repr_escapes_c1_control_chars() -> None:
    """repr(Todo) should escape C1 control characters (0x80-0x9f)."""
    # C1 control character (0x85 is NEL - Next Line)
    text_with_c1 = "text\x85more"
    todo = Todo(id=5, text=text_with_c1)
    result = repr(todo)

    # Should have escaped representation
    assert "\\x85" in result, f"repr should have escaped C1 control: {result!r}"


def test_todo_repr_escapes_del_char() -> None:
    """repr(Todo) should escape DEL character (0x7f)."""
    text_with_del = "text\x7fmore"
    todo = Todo(id=6, text=text_with_del)
    result = repr(todo)

    # Should have escaped representation
    assert "\\x7f" in result, f"repr should have escaped DEL: {result!r}"
