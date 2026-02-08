"""Regression tests for Issue #2347: Add priority field support.

This test file ensures that:
1. Todo class has a priority field with default value 0
2. Todo.from_dict correctly parses priority field from JSON
3. TodoFormatter.format_todo displays priority markers [P1], [P2], [P3] for non-zero priorities
4. Priority 0 (no priority) doesn't display any marker
"""

from __future__ import annotations

import pytest

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_todo_has_default_priority_zero() -> None:
    """Todo created without priority should default to 0 (no priority)."""
    todo = Todo(id=1, text="Buy milk")
    assert todo.priority == 0


def test_todo_can_set_priority() -> None:
    """Todo can be created with a specific priority value."""
    todo = Todo(id=1, text="Urgent task", priority=3)
    assert todo.priority == 3


def test_todo_to_dict_includes_priority() -> None:
    """Todo.to_dict should include the priority field."""
    todo = Todo(id=1, text="Task with priority", priority=2)
    data = todo.to_dict()
    assert data["priority"] == 2


def test_todo_from_dict_parses_priority() -> None:
    """Todo.from_dict should correctly parse priority from JSON data."""
    data = {"id": 1, "text": "Task", "priority": 3}
    todo = Todo.from_dict(data)
    assert todo.priority == 3


def test_todo_from_dict_defaults_priority_to_zero() -> None:
    """Todo.from_dict should default priority to 0 when not provided."""
    data = {"id": 1, "text": "Task"}
    todo = Todo.from_dict(data)
    assert todo.priority == 0


def test_todo_from_dict_validates_priority_is_integer() -> None:
    """Todo.from_dict should reject non-integer priority values."""
    with pytest.raises(ValueError, match=r"invalid.*'priority'|'priority'.*integer"):
        Todo.from_dict({"id": 1, "text": "Task", "priority": "high"})


def test_todo_from_dict_validates_priority_range() -> None:
    """Todo.from_dict should reject priority values outside 0-3 range."""
    with pytest.raises(ValueError, match=r"invalid.*'priority'|'priority'.*range"):
        Todo.from_dict({"id": 1, "text": "Task", "priority": -1})

    with pytest.raises(ValueError, match=r"invalid.*'priority'|'priority'.*range"):
        Todo.from_dict({"id": 1, "text": "Task", "priority": 4})


def test_format_todo_without_priority_shows_no_marker() -> None:
    """format_todo should not show priority marker when priority is 0."""
    todo = Todo(id=1, text="Normal task", priority=0)
    result = TodoFormatter.format_todo(todo)
    assert "[P" not in result
    assert result == "[ ]   1 Normal task"


def test_format_todo_with_priority_1_shows_p1_marker() -> None:
    """format_todo should show [P1] marker when priority is 1 (low)."""
    todo = Todo(id=1, text="Low priority task", priority=1)
    result = TodoFormatter.format_todo(todo)
    assert "[P1]" in result
    # P1 marker should appear before the task text
    assert "[P1]" in result
    assert "Low priority task" in result


def test_format_todo_with_priority_2_shows_p2_marker() -> None:
    """format_todo should show [P2] marker when priority is 2 (medium)."""
    todo = Todo(id=1, text="Medium priority task", priority=2)
    result = TodoFormatter.format_todo(todo)
    assert "[P2]" in result
    assert "Medium priority task" in result


def test_format_todo_with_priority_3_shows_p3_marker() -> None:
    """format_todo should show [P3] marker when priority is 3 (high)."""
    todo = Todo(id=1, text="High priority task", priority=3)
    result = TodoFormatter.format_todo(todo)
    assert "[P3]" in result
    assert "High priority task" in result


def test_format_todo_with_done_status_and_priority() -> None:
    """format_todo should show both done status and priority marker."""
    todo = Todo(id=1, text="Done high priority task", priority=3, done=True)
    result = TodoFormatter.format_todo(todo)
    assert "[x]" in result
    assert "[P3]" in result
    assert "Done high priority task" in result


def test_format_list_with_mixed_priorities() -> None:
    """format_list should correctly format todos with different priorities."""
    todos = [
        Todo(id=1, text="No priority task", priority=0),
        Todo(id=2, text="Low priority task", priority=1),
        Todo(id=3, text="High priority task", priority=3),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    assert len(lines) == 3
    # First line: no priority marker
    assert "[P" not in lines[0]
    # Second line: P1 marker
    assert "[P1]" in lines[1]
    # Third line: P3 marker
    assert "[P3]" in lines[2]
