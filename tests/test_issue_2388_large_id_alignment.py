"""Regression tests for Issue #2388: format_todo ID alignment for large IDs.

This test file ensures that todo IDs >= 1000 are properly aligned in output.
The original implementation used fixed width (>3) which causes misalignment
for IDs with 4 or more digits.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_with_id_1000() -> None:
    """Todo with ID 1000 should be properly aligned (4 digits)."""
    todo = Todo(id=1000, text="Buy milk")
    result = TodoFormatter.format_todo(todo)
    # Should properly format 4-digit ID
    assert result == "[ ] 1000 Buy milk"


def test_format_todo_with_id_99999() -> None:
    """Todo with ID 99999 should be properly aligned (5 digits)."""
    todo = Todo(id=99999, text="Large ID task")
    result = TodoFormatter.format_todo(todo)
    # Should properly format 5-digit ID
    assert result == "[ ] 99999 Large ID task"


def test_format_list_with_varying_id_widths() -> None:
    """Multiple todos with varying ID widths should be aligned consistently."""
    todos = [
        Todo(id=1, text="Small ID"),
        Todo(id=999, text="Three digit ID"),
        Todo(id=1000, text="Four digit ID"),
        Todo(id=99999, text="Five digit ID"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # All lines should be aligned to max ID width (5 digits for 99999)
    assert lines[0] == "[ ]     1 Small ID"
    assert lines[1] == "[ ]   999 Three digit ID"
    assert lines[2] == "[ ]  1000 Four digit ID"
    assert lines[3] == "[ ] 99999 Five digit ID"


def test_format_todo_with_large_id_done() -> None:
    """Completed todo with large ID should be properly aligned."""
    todo = Todo(id=5000, text="Done task", done=True)
    result = TodoFormatter.format_todo(todo)
    # Should properly format 4-digit ID when done
    assert result == "[x] 5000 Done task"
