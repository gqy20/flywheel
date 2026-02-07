"""Regression tests for Issue #2042: DEL and C1 control character sanitization.

This test file ensures that DEL (0x7f) and C1 control characters (0x80-0x9f)
in todo.text are properly escaped to prevent terminal output manipulation.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_escapes_del_character() -> None:
    """DEL character (0x7f) should be escaped to \\x7f."""
    todo = Todo(id=1, text="before\x7fafter")
    result = TodoFormatter.format_todo(todo)
    assert "\\x7f" in result
    assert "\x7f" not in result


def test_format_todo_escapes_c1_control_chars() -> None:
    """C1 control characters (0x80-0x9f) should be escaped."""
    todo = Todo(id=1, text="before\x8dafter")
    result = TodoFormatter.format_todo(todo)
    assert "\\x8d" in result
    assert "\x8d" not in result


def test_format_todo_escapes_multiple_c1_controls() -> None:
    """Multiple C1 control characters should all be escaped."""
    todo = Todo(id=1, text="start\x80\x90\x9fend")
    result = TodoFormatter.format_todo(todo)
    assert "\\x80" in result
    assert "\\x90" in result
    assert "\\x9f" in result
    assert "\x80" not in result
    assert "\x90" not in result
    assert "\x9f" not in result


def test_format_todo_escapes_mixed_del_and_c1() -> None:
    """DEL and C1 controls mixed together should all be escaped."""
    todo = Todo(id=1, text="text\x7fwith\x85mixed\x9acontrols")
    result = TodoFormatter.format_todo(todo)
    assert "\\x7f" in result
    assert "\\x85" in result
    assert "\\x9a" in result
    assert "\x7f" not in result
    assert "\x85" not in result
    assert "\x9a" not in result


def test_format_todo_boundary_7e_7f_80() -> None:
    """Test boundary around DEL and C1: 0x7e (~), 0x7f (DEL), 0x80 (C1 start)."""
    todo = Todo(id=1, text="\x7e\x7f\x80")
    result = TodoFormatter.format_todo(todo)
    # 0x7e (~) should pass through unchanged
    assert "~" in result
    # 0x7f should be escaped
    assert "\\x7f" in result
    assert "\x7f" not in result
    # 0x80 should be escaped
    assert "\\x80" in result
    assert "\x80" not in result


def test_format_todo_boundary_9f_a0() -> None:
    """Test boundary around C1 end: 0x9f (C1 end), 0xa0 (NBSP - not a control)."""
    todo = Todo(id=1, text="\x9f\xa0")
    result = TodoFormatter.format_todo(todo)
    # 0x9f should be escaped
    assert "\\x9f" in result
    assert "\x9f" not in result
    # 0xa0 (NO-BREAK SPACE) is not a control char, should pass through
    assert "\xa0" in result
