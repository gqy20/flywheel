"""Regression tests for Issue #2042: DEL and C1 control character sanitization.

This test file ensures that DEL (0x7f) and C1 control characters (0x80-0x9f)
in todo.text are properly escaped to prevent terminal output manipulation.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_escapes_del_char() -> None:
    """DEL character (0x7f) should be escaped to \\x7f."""
    todo = Todo(id=1, text="before\x7fafter")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\x7f" in result
    # Should not contain actual DEL character
    assert "\x7f" not in result


def test_format_todo_escapes_c1_control_chars() -> None:
    """C1 control characters (0x80-0x9f) should be escaped."""
    # Test a few representative C1 control characters
    test_cases = [
        (0x80, "\\x80"),  # PAD
        (0x8d, "\\x8d"),  # RI
        (0x9f, "\\x9f"),  # APC
    ]
    for code, expected in test_cases:
        todo = Todo(id=1, text=f"before{chr(code)}after")
        result = TodoFormatter.format_todo(todo)
        assert expected in result, f"Expected {expected} in result for code {code:#x}"
        assert chr(code) not in result, f"Actual character {code:#x} should not be in result"


def test_format_todo_escapes_all_c1_range() -> None:
    """All C1 control characters (0x80-0x9f) should be escaped."""
    for code in range(0x80, 0xa0):
        todo = Todo(id=1, text=f"text{chr(code)}end")
        result = TodoFormatter.format_todo(todo)
        # Should not contain actual C1 control character
        assert chr(code) not in result, f"C1 control character {code:#x} not escaped"
        # Should contain escaped representation
        assert f"\\x{code:02x}" in result


def test_format_todo_escapes_mixed_del_and_c1() -> None:
    """Mix of DEL and C1 controls should all be escaped."""
    todo = Todo(id=1, text="start\x7fmiddle\x90end")
    result = TodoFormatter.format_todo(todo)
    assert "\\x7f" in result
    assert "\\x90" in result
    assert "\x7f" not in result
    assert "\x90" not in result


def test_format_todo_escapes_del_with_existing_controls() -> None:
    """DEL and C1 should be escaped alongside existing control character handling."""
    todo = Todo(id=1, text="text\n\x7f\r\x80end")
    result = TodoFormatter.format_todo(todo)
    # All should be escaped
    assert "\\n" in result
    assert "\\x7f" in result
    assert "\\r" in result
    assert "\\x80" in result
    # No actual control characters
    assert "\n" not in result
    assert "\x7f" not in result
    assert "\r" not in result
    assert "\x80" not in result
