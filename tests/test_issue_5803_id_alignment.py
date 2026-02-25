"""Regression tests for Issue #5803: ID format alignment for large IDs.

This test file ensures that the ID column remains properly aligned
when IDs are >= 1000 or have varying digit counts.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_id_999_alignment() -> None:
    """ID=999 should output properly aligned format."""
    todo = Todo(id=999, text="Test task")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ] 999 Test task"


def test_format_todo_id_1000_alignment() -> None:
    """ID=1000 should maintain column alignment without breaking format."""
    todo = Todo(id=1000, text="Test task")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ] 1000 Test task"


def test_format_todo_id_10000_alignment() -> None:
    """ID=10000 should maintain column alignment."""
    todo = Todo(id=10000, text="Test task")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ] 10000 Test task"


def test_format_todo_id_0_alignment() -> None:
    """ID=0 should output properly aligned format."""
    todo = Todo(id=0, text="Test task")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ] 0 Test task"


def test_format_todo_negative_id_readable() -> None:
    """Negative ID (edge case) should produce readable output."""
    todo = Todo(id=-1, text="Test task")
    result = TodoFormatter.format_todo(todo)
    # Should be readable, not breaking the format
    assert "[ ]" in result
    assert "Test task" in result


def test_format_list_column_alignment_consistency() -> None:
    """Multiple todos with varying ID widths should maintain column alignment."""
    todos = [
        Todo(id=1, text="Task one"),
        Todo(id=100, text="Task hundred"),
        Todo(id=1000, text="Task thousand"),
        Todo(id=10000, text="Task ten thousand"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # All lines should have "[ ]" prefix followed by ID
    assert len(lines) == 4

    # Verify column alignment: all IDs should start at the same position
    # The format is "[ ] {id} {text}"
    # After "[ ] " (4 chars), IDs should be right-aligned with dynamic width
    for line in lines:
        assert line.startswith("[ ] ")

    # Verify specific outputs for each line
    assert lines[0] == "[ ]     1 Task one"
    assert lines[1] == "[ ]   100 Task hundred"
    assert lines[2] == "[ ]  1000 Task thousand"
    assert lines[3] == "[ ] 10000 Task ten thousand"


def test_format_list_all_large_ids_aligned() -> None:
    """All large IDs should be aligned consistently."""
    todos = [
        Todo(id=1000, text="First"),
        Todo(id=1001, text="Second"),
        Todo(id=9999, text="Last"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # All IDs should be 4-digit width, aligned
    assert lines[0] == "[ ] 1000 First"
    assert lines[1] == "[ ] 1001 Second"
    assert lines[2] == "[ ] 9999 Last"
