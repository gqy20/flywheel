"""Regression tests for Issue #2347: Priority field support.

This test file ensures that:
1. Todo class has a priority field with default value of 0
2. Todo.from_dict correctly parses priority field
3. TodoFormatter.format_todo displays priority markers when priority is non-zero
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_todo_has_default_priority_zero() -> None:
    """Todo created without priority should default to 0."""
    todo = Todo(id=1, text="Buy groceries")
    assert todo.priority == 0


def test_todo_can_set_priority() -> None:
    """Todo should accept priority values 0-3."""
    todo_low = Todo(id=1, text="Low priority task", priority=1)
    assert todo_low.priority == 1

    todo_medium = Todo(id=2, text="Medium priority task", priority=2)
    assert todo_medium.priority == 2

    todo_high = Todo(id=3, text="High priority task", priority=3)
    assert todo_high.priority == 3


def test_todo_to_dict_includes_priority() -> None:
    """Todo.to_dict should include the priority field."""
    todo = Todo(id=1, text="Task with priority", priority=2)
    data = todo.to_dict()
    assert "priority" in data
    assert data["priority"] == 2


def test_todo_from_dict_parses_priority() -> None:
    """Todo.from_dict should correctly parse the priority field."""
    data = {
        "id": 1,
        "text": "Task with priority",
        "done": False,
        "priority": 3,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    }
    todo = Todo.from_dict(data)
    assert todo.priority == 3


def test_todo_from_dict_defaults_priority_to_zero() -> None:
    """Todo.from_dict should default priority to 0 when not provided."""
    data = {
        "id": 1,
        "text": "Task without priority",
        "done": False,
    }
    todo = Todo.from_dict(data)
    assert todo.priority == 0


def test_format_todo_without_priority_shows_no_marker() -> None:
    """Todo with priority=0 should not show priority marker."""
    todo = Todo(id=1, text="Normal task", priority=0)
    result = TodoFormatter.format_todo(todo)
    assert "[P1]" not in result
    assert "[P2]" not in result
    assert "[P3]" not in result


def test_format_todo_with_priority_1_shows_p1_marker() -> None:
    """Todo with priority=1 should show [P1] marker."""
    todo = Todo(id=1, text="Low priority task", priority=1)
    result = TodoFormatter.format_todo(todo)
    assert "[P1]" in result


def test_format_todo_with_priority_2_shows_p2_marker() -> None:
    """Todo with priority=2 should show [P2] marker."""
    todo = Todo(id=2, text="Medium priority task", priority=2)
    result = TodoFormatter.format_todo(todo)
    assert "[P2]" in result


def test_format_todo_with_priority_3_shows_p3_marker() -> None:
    """Todo with priority=3 should show [P3] marker."""
    todo = Todo(id=3, text="High priority task", priority=3)
    result = TodoFormatter.format_todo(todo)
    assert "[P3]" in result


def test_format_list_with_priorities() -> None:
    """Multiple todos with different priorities should display correctly."""
    todos = [
        Todo(id=1, text="Low priority", priority=1),
        Todo(id=2, text="Normal task", priority=0),
        Todo(id=3, text="High priority", priority=3),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")
    assert "[P1]" in lines[0]
    assert "[P1]" not in lines[1]  # priority 0 has no marker
    assert "[P3]" in lines[2]
