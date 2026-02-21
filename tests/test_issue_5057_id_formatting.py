"""Regression tests for Issue #5057: ID formatting with fixed width causes alignment issues.

This test file ensures that ID formatting handles:
- Negative IDs correctly (no misalignment)
- Large IDs (>= 1000) correctly (no truncation)
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_negative_id_alignment() -> None:
    """Negative ID should not cause misalignment in output."""
    todo = Todo(id=-1, text="Negative ID task")
    result = TodoFormatter.format_todo(todo)
    # The ID should be displayed as-is without fixed width padding issues
    # -1 should appear in output (not truncated or misaligned)
    assert "-1" in result
    # Check consistent format: [ ] <id> <text>
    assert result.startswith("[ ] -1 Negative ID task")


def test_format_todo_large_id_no_truncation() -> None:
    """Large ID (>= 1000) should not be truncated in output."""
    todo = Todo(id=999999, text="Large ID task")
    result = TodoFormatter.format_todo(todo)
    # The full ID should appear in output
    assert "999999" in result
    # Check format: [ ] <id> <text>
    assert result.startswith("[ ] 999999 Large ID task")


def test_format_list_with_mixed_id_sizes() -> None:
    """List with mixed ID sizes should have consistent formatting."""
    todos = [
        Todo(id=1, text="Small ID"),
        Todo(id=999999, text="Large ID"),
        Todo(id=-1, text="Negative ID"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")
    assert len(lines) == 3

    # Each line should have its ID present
    assert "1" in lines[0]
    assert "999999" in lines[1]
    assert "-1" in lines[2]

    # All lines should follow [ ] <id> <text> pattern
    assert "[ ] 1 " in lines[0]
    assert "[ ] 999999 " in lines[1]
    assert "[ ] -1 " in lines[2]
