"""Regression tests for Issue #5057: ID formatting alignment inconsistency.

This test file ensures that ID formatting works correctly for edge cases:
- Negative IDs
- Large IDs (>= 1000)
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_negative_id() -> None:
    """Negative ID should display correctly without alignment issues."""
    todo = Todo(id=-1, text="Negative ID task")
    result = TodoFormatter.format_todo(todo)
    # Should contain the negative ID correctly
    assert "-1" in result
    # Should be properly formatted
    assert result == "[ ] -1 Negative ID task"


def test_format_todo_large_id() -> None:
    """Large ID (>= 1000) should display correctly without truncation."""
    todo = Todo(id=999999, text="Large ID task")
    result = TodoFormatter.format_todo(todo)
    # Should contain the full ID without truncation
    assert "999999" in result
    # Should be properly formatted
    assert result == "[ ] 999999 Large ID task"


def test_format_todo_id_999() -> None:
    """ID at boundary (999) should display correctly."""
    todo = Todo(id=999, text="Boundary ID task")
    result = TodoFormatter.format_todo(todo)
    assert "999" in result
    assert result == "[ ] 999 Boundary ID task"


def test_format_todo_id_1000() -> None:
    """ID just above boundary (1000) should display correctly."""
    todo = Todo(id=1000, text="Over boundary ID task")
    result = TodoFormatter.format_todo(todo)
    assert "1000" in result
    assert result == "[ ] 1000 Over boundary ID task"


def test_format_list_with_mixed_ids() -> None:
    """List with mixed ID sizes should display all correctly."""
    todos = [
        Todo(id=1, text="Small ID"),
        Todo(id=-5, text="Negative ID"),
        Todo(id=999999, text="Large ID"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")
    assert len(lines) == 3
    assert "1" in lines[0]
    assert "-5" in lines[1]
    assert "999999" in lines[2]
