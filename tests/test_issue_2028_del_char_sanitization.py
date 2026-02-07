"""Regression tests for Issue #2028: DEL character (0x7f) sanitization.

This test file ensures that the DEL character (0x7f/127) is properly escaped
to prevent terminal manipulation in some terminals.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_escapes_del_char() -> None:
    """DEL character (0x7f) should be escaped to prevent terminal manipulation."""
    todo = Todo(id=1, text="Normal\x7fAfter")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\x7f" in result
    # Should not contain actual DEL character
    assert "\x7f" not in result


def test_format_todo_escapes_standalone_del_char() -> None:
    """Standalone DEL character should be escaped."""
    todo = Todo(id=1, text="\x7f")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ]   1 \\x7f"
    assert "\x7f" not in result


def test_format_todo_escapes_multiple_del_chars() -> None:
    """Multiple DEL characters should all be escaped."""
    todo = Todo(id=1, text="\x7f\x7f\x7f")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ]   1 \\x7f\\x7f\\x7f"
    assert "\x7f" not in result
