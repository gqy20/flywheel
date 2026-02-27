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


def test_format_todo_escapes_unicode_line_separator() -> None:
    """Unicode line separator (U+2028) should be escaped to prevent log injection."""
    # U+2028 is a Unicode line separator that creates line breaks in JSON and some displays
    todo = Todo(id=1, text="Before\u2028After")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\u2028" in result
    # Should not contain actual U+2028 character
    assert "\u2028" not in result


def test_format_todo_escapes_unicode_paragraph_separator() -> None:
    """Unicode paragraph separator (U+2029) should be escaped to prevent log injection."""
    # U+2029 is a Unicode paragraph separator that creates line breaks in JSON and some displays
    todo = Todo(id=1, text="Before\u2029After")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\u2029" in result
    # Should not contain actual U+2029 character
    assert "\u2029" not in result


def test_format_todo_escapes_both_unicode_separators() -> None:
    """Both U+2028 and U+2029 should be escaped in the same string."""
    todo = Todo(id=1, text="Line1\u2028Line2\u2029Para2")
    result = TodoFormatter.format_todo(todo)
    assert "\\u2028" in result
    assert "\\u2029" in result
    # Should not contain actual separator characters
    assert "\u2028" not in result
    assert "\u2029" not in result
