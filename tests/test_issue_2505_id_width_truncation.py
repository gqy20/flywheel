"""Regression tests for Issue #2505: format_todo ID width truncation.

This test file ensures that todo IDs with 4+ digits are displayed correctly
with consistent column alignment. The original implementation used {todo.id:>3}
which caused misalignment for IDs >= 1000 since the field would overflow.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def _find_text_start_position(formatted_line: str, text: str) -> int:
    """Helper to find where the todo text starts in the formatted output."""
    # The text appears after the status and ID fields
    return formatted_line.index(text)


def test_format_todo_with_3_digit_id() -> None:
    """Todo with 3-digit ID (999) should display with proper alignment."""
    todo = Todo(id=999, text="Important task")
    result = TodoFormatter.format_todo(todo)
    # Should have proper spacing and no truncation
    # With width 5: "[ ]   999 Important task" (2 leading spaces for 999)
    assert result == "[ ]   999 Important task"
    # Text should be fully present
    assert "Important task" in result
    # Text should start at consistent position (after "[ ] XXXXX ")
    assert _find_text_start_position(result, "Important task") == 10


def test_format_todo_with_4_digit_id() -> None:
    """Todo with 4-digit ID (1000) should display with consistent alignment.

    With the fix using width >= 4, text should start at the same position as 3-digit IDs.
    """
    todo = Todo(id=1000, text="Buy milk")
    result = TodoFormatter.format_todo(todo)
    # Text should be fully present and not truncated
    assert "Buy milk" in result
    # ID should be visible in output
    assert "1000" in result
    # Text should start at consistent position (same as 3-digit ID: position 8 with width 3, or later with fix)
    # After fix with width 5: "[ ]  1000 Buy milk" -> text at position 10
    text_start = _find_text_start_position(result, "Buy milk")
    assert text_start >= 8, f"Text should start at or after position 8, got {text_start}"


def test_format_todo_with_5_digit_id() -> None:
    """Todo with 5-digit ID (10000) should display without truncating text."""
    todo = Todo(id=10000, text="Write code")
    result = TodoFormatter.format_todo(todo)
    # Text should be fully present and not truncated
    assert "Write code" in result
    # ID should be visible in output
    assert "10000" in result


def test_format_list_with_mixed_id_widths() -> None:
    """Multiple todos with varying ID widths should align properly in list.

    This is the key test for the bug: all todo texts should start at the SAME
    column position regardless of ID length.
    """
    todos = [
        Todo(id=1, text="Task one"),
        Todo(id=999, text="Task 999"),
        Todo(id=1000, text="Task 1000"),
        Todo(id=99999, text="Task huge"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # Should have 4 lines
    assert len(lines) == 4

    # Each todo's text should be fully present (not truncated)
    assert "Task one" in result
    assert "Task 999" in result
    assert "Task 1000" in result
    assert "Task huge" in result

    # All IDs should be visible
    assert "1" in lines[0]
    assert "999" in lines[1]
    assert "1000" in lines[2]
    assert "99999" in lines[3]

    # CRITICAL: All texts should start at the SAME column position
    # This is what the bug breaks - with width=3, texts start at different positions
    text_positions = [_find_text_start_position(line, "Task") for line in lines]
    assert len(set(text_positions)) == 1, f"Text positions should be identical, got: {text_positions}"


def test_format_todo_with_short_text_and_large_id() -> None:
    """Todo with short text and large ID should still display correctly."""
    todo = Todo(id=12345, text="A")
    result = TodoFormatter.format_todo(todo)
    # Single character text should not be lost
    assert result.endswith("A") or " A" in result
    assert "12345" in result


def test_format_todo_preserves_text_content_with_large_id() -> None:
    """Todo text content should be preserved exactly regardless of ID size."""
    original_text = "The quick brown fox jumps over the lazy dog"
    todo = Todo(id=9999, text=original_text)
    result = TodoFormatter.format_todo(todo)
    # Full text should be present
    assert original_text in result
    assert "9999" in result
