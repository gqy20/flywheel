"""Tests for control character sanitization (Issue #1948).

Security: Control characters in todo.text must be sanitized to prevent
terminal injection via ANSI escape sequences or newline/carriage return attacks.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_sanitizes_newline() -> None:
    """Newline characters should be escaped or removed."""
    todo = Todo(id=1, text="buy milk\nand bread")
    result = TodoFormatter.format_todo(todo)
    # The newline should not create actual newlines in output
    assert "\n" not in result
    assert "buy milk" in result


def test_format_todo_sanitizes_carriage_return() -> None:
    """Carriage return characters should be escaped or removed."""
    todo = Todo(id=1, text="task 1\rDo something else")
    result = TodoFormatter.format_todo(todo)
    # The carriage return should not affect output
    assert "\r" not in result


def test_format_todo_sanitizes_ansi_escape_sequences() -> None:
    """ANSI escape sequences should be escaped or removed."""
    # Red text ANSI sequence
    todo = Todo(id=1, text="normal text\x1b[31mRED TEXT\x1b[0mnormal again")
    result = TodoFormatter.format_todo(todo)
    # The ANSI escape character should be removed or escaped
    assert "\x1b" not in result


def test_format_todo_sanitizes_tab_characters() -> None:
    """Tab characters should be escaped or removed."""
    todo = Todo(id=1, text="column1\tcolumn2")
    result = TodoFormatter.format_todo(todo)
    # Tabs should not create actual tab spacing in output
    assert "\t" not in result


def test_format_todo_sanitizes_null_bytes() -> None:
    """Null bytes should be escaped or removed."""
    todo = Todo(id=1, text="text\x00with\x00nulls")
    result = TodoFormatter.format_todo(todo)
    # Null bytes should be removed
    assert "\x00" not in result


def test_format_todo_normal_text_unchanged() -> None:
    """Normal todo text should pass through unchanged."""
    todo = Todo(id=1, text="buy milk and bread")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ]   1 buy milk and bread"


def test_format_list_sanitizes_control_chars() -> None:
    """format_list should also sanitize control characters in todo text."""
    todos = [
        Todo(id=1, text="normal task"),
        Todo(id=2, text="task\rwith\rcarriage"),
        Todo(id=3, text="task\x1b[31mwith ANSI"),
    ]
    result = TodoFormatter.format_list(todos)
    # Control characters from todo text should be sanitized
    assert "\r" not in result
    assert "\x1b" not in result
    # Normal text should be preserved
    assert "normal task" in result
    # Todo text with removed control chars should be present
    assert "taskwithcarriage" in result
