"""Regression tests for issue #1948: Control character sanitization in formatter.

Issue: Control characters in todo.text are not sanitized, allowing terminal injection
via ANSI escape sequences or newline/carriage return attacks.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_sanitizes_newline() -> None:
    """Issue #1948: Newline characters should be sanitized in output."""
    todo = Todo(id=1, text="Buy milk\nAnd eggs")
    result = TodoFormatter.format_todo(todo)

    # Output should not contain actual newlines
    assert "\n" not in result, "Newlines should be sanitized from output"
    # Should be a single line
    lines = result.split("\n")
    assert len(lines) == 1, f"Output should be single line, got {len(lines)} lines"


def test_format_todo_sanitizes_carriage_return() -> None:
    """Issue #1948: Carriage return characters should be sanitized in output."""
    todo = Todo(id=1, text="Task\rWith carriage return")
    result = TodoFormatter.format_todo(todo)

    assert "\r" not in result, "Carriage returns should be sanitized from output"


def test_format_todo_sanitizes_tab() -> None:
    """Issue #1948: Tab characters should be sanitized in output."""
    todo = Todo(id=1, text="Task\tWith\tTabs")
    result = TodoFormatter.format_todo(todo)

    # Tabs can be either removed or replaced with spaces
    # Just verify they don't appear as raw tabs
    # (or check that output renders safely without breaking structure)
    assert "\t" not in result, "Tabs should be sanitized from output"


def test_format_todo_sanitizes_null_byte() -> None:
    """Issue #1948: Null bytes should be sanitized in output."""
    todo = Todo(id=1, text="Task\x00With\x00Nulls")
    result = TodoFormatter.format_todo(todo)

    assert "\x00" not in result, "Null bytes should be sanitized from output"


def test_format_todo_sanitizes_ansi_escape_sequences() -> None:
    """Issue #1948: ANSI escape sequences should be sanitized from output."""
    # Common ANSI escape for red text
    todo = Todo(id=1, text="\x1b[31mRed text\x1b[0m")
    result = TodoFormatter.format_todo(todo)

    # ESC character should be removed
    assert "\x1b" not in result, "ANSI escape character should be sanitized from output"


def test_format_todo_preserves_normal_text() -> None:
    """Issue #1948: Normal text without control characters should be unchanged."""
    todo = Todo(id=1, text="Normal todo text with spaces and punctuation!")
    result = TodoFormatter.format_todo(todo)

    # Should contain the original text
    assert "Normal todo text with spaces and punctuation!" in result


def test_format_todo_sanitizes_combined_control_chars() -> None:
    """Issue #1948: Multiple control characters should all be sanitized."""
    todo = Todo(id=1, text="Text\nwith\rmany\t\x00control\x1b[31mchars")
    result = TodoFormatter.format_todo(todo)

    # All dangerous control chars should be removed
    assert "\n" not in result
    assert "\r" not in result
    assert "\t" not in result
    assert "\x00" not in result
    assert "\x1b" not in result


def test_format_list_sanitizes_all_todos() -> None:
    """Issue #1948: format_list should sanitize control characters in all todos."""
    todos = [
        Todo(id=1, text="Normal task"),
        Todo(id=2, text="Task\nWith\nNewlines"),
        Todo(id=3, text="Task\rWithCR"),
        Todo(id=4, text="\x1b[31mColored\x1b[0m task"),
    ]
    result = TodoFormatter.format_list(todos)

    # Result should be multiple lines (one per todo)
    lines = result.split("\n")

    # Should have 4 lines (one for each todo)
    assert len(lines) == 4, f"Expected 4 lines, got {len(lines)}"

    # No line should contain dangerous control characters
    for line in lines:
        assert "\r" not in line, "No carriage returns in any line"
        assert "\x00" not in line, "No null bytes in any line"
        assert "\x1b" not in line, "No ANSI escapes in any line"
