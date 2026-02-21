"""Regression tests for Issue #5057: ID formatting with fixed width causes misalignment.

This test file ensures that ID formatting works correctly for:
- Negative IDs
- IDs >= 1000
- Regular positive IDs (1-999)

The fixed width (>3) format only works for IDs 1-999 and causes
misalignment for negative IDs and IDs >= 1000.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_negative_id() -> None:
    """Todo with negative ID should display correctly without misalignment."""
    todo = Todo(id=-1, text="Negative ID task")
    result = TodoFormatter.format_todo(todo)
    # Should contain the negative ID without alignment issues
    assert "-1" in result
    # The ID should be directly placed without fixed-width padding
    assert result == "[ ] -1 Negative ID task"


def test_format_todo_large_id() -> None:
    """Todo with ID >= 1000 should display correctly without truncation."""
    todo = Todo(id=999999, text="Large ID task")
    result = TodoFormatter.format_todo(todo)
    # Should contain the full ID without truncation
    assert "999999" in result
    # The ID should be directly placed without fixed-width padding
    assert result == "[ ] 999999 Large ID task"


def test_format_todo_id_999() -> None:
    """Todo with ID 999 should still display correctly."""
    todo = Todo(id=999, text="ID 999 task")
    result = TodoFormatter.format_todo(todo)
    # Should contain 999 without any padding
    assert result == "[ ] 999 ID 999 task"


def test_format_todo_id_1000() -> None:
    """Todo with ID 1000 should display correctly at boundary."""
    todo = Todo(id=1000, text="ID 1000 task")
    result = TodoFormatter.format_todo(todo)
    # Should contain 1000 without any padding
    assert result == "[ ] 1000 ID 1000 task"


def test_format_list_with_mixed_ids() -> None:
    """List with various ID ranges should display consistently."""
    todos = [
        Todo(id=1, text="Small ID"),
        Todo(id=999, text="Max 3-digit"),
        Todo(id=1000, text="Min 4-digit"),
        Todo(id=-5, text="Negative ID"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")
    # Each line should contain the ID directly after the status bracket
    assert "1 Small ID" in lines[0]
    assert "999 Max 3-digit" in lines[1]
    assert "1000 Min 4-digit" in lines[2]
    assert "-5 Negative ID" in lines[3]
