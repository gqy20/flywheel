"""Regression tests for Issue #1924: format_todo control character sanitization.

This test file ensures that control characters in todo.text are properly escaped
to prevent terminal output manipulation.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_escapes_newline_in_text() -> None:
    """Todo with \\n in text should output escaped newline, not actual newline."""
    todo = Todo(id=1, text="Buy milk\n[ ] FAKE_TODO")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation, not actual newline
    assert "\\n" in result
    # Should be single line (no actual newline character)
    assert "\n" not in result
    # Should show both parts on same line
    assert result == "[ ]   1 Buy milk\\n[ ] FAKE_TODO"


def test_format_todo_escapes_carriage_return_in_text() -> None:
    """Todo with \\r in text should be escaped, not overwrite output."""
    todo = Todo(id=1, text="Valid task\r[ ] FAKE")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\r" in result
    # Should not contain actual carriage return
    assert "\r" not in result


def test_format_todo_escapes_tab_in_text() -> None:
    """Todo with \\t in text should be escaped visibly."""
    todo = Todo(id=1, text="Task\twith\ttabs")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\t" in result
    # Should not contain actual tab character
    assert "\t" not in result


def test_format_todo_escapes_multiple_control_chars() -> None:
    """Todo with mixed control characters should all be escaped."""
    todo = Todo(id=1, text="Line1\nLine2\rTab\tHere")
    result = TodoFormatter.format_todo(todo)
    assert "\\n" in result
    assert "\\r" in result
    assert "\\t" in result
    # Should not contain actual control characters
    assert "\n" not in result
    assert "\r" not in result
    assert "\t" not in result


def test_format_todo_escapes_ansi_codes_in_text() -> None:
    """ANSI escape sequences should be escaped to prevent terminal injection."""
    todo = Todo(id=1, text="\x1b[31mRed Text\x1b[0m Normal")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\x1b" in result
    # Should not contain actual ESC character
    assert "\x1b" not in result


def test_format_todo_escapes_null_byte() -> None:
    """Null byte should be escaped."""
    todo = Todo(id=1, text="Before\x00After")
    result = TodoFormatter.format_todo(todo)
    assert "\\x00" in result
    assert "\x00" not in result


def test_format_todo_normal_text_unchanged() -> None:
    """Normal todo text without control characters should be unchanged."""
    todo = Todo(id=1, text="Buy groceries")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ]   1 Buy groceries"


def test_format_todo_with_unicode() -> None:
    """Unicode characters should pass through unchanged."""
    todo = Todo(id=1, text="Buy café and 日本語")
    result = TodoFormatter.format_todo(todo)
    assert "café" in result
    assert "日本語" in result


def test_format_list_with_malicious_todos() -> None:
    """Multiple malicious todos should each be sanitized in list output."""
    todos = [
        Todo(id=1, text="Task 1\nFake task"),
        Todo(id=2, text="Task 2\tTabbed"),
        Todo(id=3, text="Normal task"),
    ]
    result = TodoFormatter.format_list(todos)
    # Each todo should be on its own line (3 lines total)
    lines = result.split("\n")
    assert len(lines) == 3
    # The fake tasks should be escaped
    assert "\\n" in lines[0]
    assert "\\t" in lines[1]
    # Normal task should be unchanged
    assert "Normal task" in lines[2]


def test_format_list_empty() -> None:
    """Empty list should return standard message."""
    result = TodoFormatter.format_list([])
    assert result == "No todos yet."


def test_format_todo_escapes_del_char_in_text() -> None:
    """DEL character (0x7f) should be escaped to prevent terminal injection."""
    todo = Todo(id=1, text="Before\x7fAfter")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\x7f" in result
    # Should not contain actual DEL character
    assert "\x7f" not in result


def test_format_todo_escapes_c1_control_chars_in_text() -> None:
    """C1 control characters (0x80-0x9f) should be escaped to prevent terminal injection."""
    # Test a representative sample of C1 controls
    # 0x8d = reverse line feed, 0x9b = CSI (control sequence introducer)
    todo = Todo(id=1, text="Before\x8dMiddle\x9bAfter")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representations
    assert "\\x8d" in result
    assert "\\x9b" in result
    # Should not contain actual C1 control characters
    assert "\x8d" not in result
    assert "\x9b" not in result


def test_format_todo_escapes_all_control_chars_comprehensive() -> None:
    """Comprehensive test covering C0, DEL, and C1 control characters."""
    # Include representatives from all control char ranges:
    # - C0: \n (0x0a)
    # - DEL: 0x7f
    # - C1: 0x80, 0x9f
    todo = Todo(id=1, text="Normal\nDel\x7fC1Start\x80C1End\x9fEnd")
    result = TodoFormatter.format_todo(todo)
    # All should be escaped
    assert "\\n" in result
    assert "\\x7f" in result
    assert "\\x80" in result
    assert "\\x9f" in result
    # Should not contain actual control characters
    assert "\n" not in result
    assert "\x7f" not in result
    assert "\x80" not in result
    assert "\x9f" not in result


def test_format_todo_escapes_del_and_c1_in_list() -> None:
    """DEL and C1 control characters should be escaped in list format."""
    todos = [
        Todo(id=1, text="Task with DEL\x7fchar"),
        Todo(id=2, text="Task with C1\x9bcontrol"),
        Todo(id=3, text="Normal task"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")
    assert len(lines) == 3
    # The control characters should be escaped
    assert "\\x7f" in lines[0]
    assert "\\x9b" in lines[1]
    # Normal task should be unchanged
    assert "Normal task" in lines[2]
