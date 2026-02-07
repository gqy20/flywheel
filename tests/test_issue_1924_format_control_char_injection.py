"""Tests for Issue #1924 - Control character injection in format_todo."""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_rejects_newline_injection() -> None:
    """Control characters like newlines should be escaped in formatted output."""
    todo = Todo(id=1, text="Buy milk\n[Evil] Malicious task")
    output = TodoFormatter.format_todo(todo)

    # Output should be a single line - no newlines allowed
    assert "\n" not in output, f"Newline character found in output: {output!r}"

    # The content should still be readable but without newlines
    assert "Buy milk" in output
    assert "[Evil]" in output  # Brackets themselves are fine, just no newlines


def test_format_todo_rejects_carriage_return_injection() -> None:
    """Control characters like carriage returns should be escaped in formatted output."""
    todo = Todo(id=1, text="Task\r\x1b[31mEvil output")
    output = TodoFormatter.format_todo(todo)

    # Output should be a single line
    assert "\r" not in output, f"Carriage return found in output: {output!r}"

    # ANSI escape codes should also be escaped
    assert "\x1b" not in output, f"ANSI escape code found in output: {output!r}"


def test_format_todo_rejects_tab_injection() -> None:
    """Tab characters should be escaped to prevent output formatting attacks."""
    todo = Todo(id=1, text="Buy\t\t\tmilk")
    output = TodoFormatter.format_todo(todo)

    # Tabs could break column alignment
    assert "\t" not in output, f"Tab character found in output: {output!r}"


def test_format_todo_rejects_multiple_control_chars() -> None:
    """Multiple control characters should all be escaped."""
    todo = Todo(id=1, text="A\nB\rC\tD\x00E\x1b[31mF")
    output = TodoFormatter.format_todo(todo)

    # Check all common control characters are escaped
    for char in ["\n", "\r", "\t", "\x00", "\x1b"]:
        assert char not in output, f"Control character {char!r} found in output: {output!r}"


def test_format_list_handles_control_chars_in_multiple_todos() -> None:
    """format_list should also sanitize control characters across multiple todos."""
    todos = [
        Todo(id=1, text="Normal task"),
        Todo(id=2, text="Malicious\n\nTask"),
        Todo(id=3, text="Another\rTask\x1b[31m"),
    ]
    output = TodoFormatter.format_list(todos)

    # Count newlines - should only be 2 (between 3 todos), not extra from malicious content
    newline_count = output.count("\n")
    assert newline_count == 2, f"Expected 2 newlines, got {newline_count} in: {output!r}"


def test_format_todo_with_normal_text_works() -> None:
    """Normal todo text should still format correctly."""
    todo = Todo(id=1, text="Buy milk and eggs")
    output = TodoFormatter.format_todo(todo)

    assert output == "[ ]   1 Buy milk and eggs"
    assert "Buy milk and eggs" in output
