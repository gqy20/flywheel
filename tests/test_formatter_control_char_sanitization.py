"""Tests for control character sanitization in TodoFormatter (issue #1948)."""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_escapes_newline_carriage_return() -> None:
    """Newline and carriage return characters should be escaped to prevent terminal injection."""
    todo = Todo(id=1, text="line1\nline2\rline3")

    result = TodoFormatter.format_todo(todo)

    # Should not contain raw newlines or carriage returns
    assert "\n" not in result
    assert "\r" not in result
    # Should be escaped
    assert "\\n" in result or result.count("line") == 1


def test_format_todo_escapes_ansi_escape_sequences() -> None:
    """ANSI escape sequences should be neutralized to prevent terminal injection."""
    todo = Todo(id=1, text="\x1b[31mred text\x1b[0m")

    result = TodoFormatter.format_todo(todo)

    # Should not contain raw escape character
    assert "\x1b" not in result
    # Should be escaped or removed
    assert "\\x1b" in result or "[31m" not in result


def test_format_todo_escapes_tab_character() -> None:
    """Tab characters should be escaped to maintain formatting."""
    todo = Todo(id=1, text="col1\tcol2")

    result = TodoFormatter.format_todo(todo)

    # Should not contain raw tab
    assert "\t" not in result
    # Should be escaped
    assert "\\t" in result or result.count("col") == 1


def test_format_todo_escapes_null_byte() -> None:
    """Null bytes should be escaped to prevent string truncation."""
    todo = Todo(id=1, text="before\x00after")

    result = TodoFormatter.format_todo(todo)

    # Should not contain raw null byte
    assert "\x00" not in result
    # Should be escaped
    assert "\\x00" in result or "after" not in result


def test_format_todo_preserves_normal_text() -> None:
    """Normal text without control characters should be unchanged."""
    todo = Todo(id=1, text="Normal todo item with numbers 123 and symbols !@#$%")

    result = TodoFormatter.format_todo(todo)

    assert "Normal todo item" in result
    assert result == "[ ]   1 Normal todo item with numbers 123 and symbols !@#$%"


def test_format_todo_escapes_backspace() -> None:
    """Backspace characters should be neutralized."""
    todo = Todo(id=1, text="abc\x08d")

    result = TodoFormatter.format_todo(todo)

    # Should not contain raw backspace
    assert "\x08" not in result
    # Should be escaped
    assert "\\x08" in result or "abcd" not in result


def test_format_list_escapes_control_chars() -> None:
    """format_list should also sanitize control characters in todo text."""
    todos = [
        Todo(id=1, text="normal"),
        Todo(id=2, text="with\nnewline"),
        Todo(id=3, text="\x1b[31mred\x1b[0m"),
    ]

    result = TodoFormatter.format_list(todos)

    # Check that control chars in TODO TEXT are escaped
    # format_list uses \n to separate todos, but the newline within the todo
    # text should be escaped
    assert "with\\nnewline" in result
    assert "\\x1b[31mred\\x1b[0m" in result
    # Raw escape should not be present in the todo text part
    assert "[ ]   3 \\x1b[31mred" in result
