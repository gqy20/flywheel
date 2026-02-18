"""Tests for Todo priority field (Issue #4091).

These tests verify that:
1. Todo class has a priority field with default value 0
2. from_dict correctly parses priority field
3. to_dict includes priority field
4. Backward compatibility with data files without priority field
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_has_priority_field_with_default_zero() -> None:
    """Todo should have a priority field with default value 0."""
    todo = Todo(id=1, text="test task")
    assert todo.priority == 0


def test_todo_can_be_created_with_priority() -> None:
    """Todo should accept priority value during creation."""
    todo = Todo(id=1, text="urgent task", priority=1)
    assert todo.priority == 1

    todo2 = Todo(id=2, text="low priority task", priority=-1)
    assert todo2.priority == -1


def test_todo_from_dict_parses_priority() -> None:
    """Todo.from_dict should correctly parse priority field."""
    todo = Todo.from_dict({"id": 1, "text": "test", "priority": 1})
    assert todo.priority == 1


def test_todo_from_dict_defaults_priority_to_zero() -> None:
    """Todo.from_dict should default priority to 0 when not provided."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.priority == 0


def test_todo_to_dict_includes_priority() -> None:
    """Todo.to_dict should include priority field."""
    todo = Todo(id=1, text="test", priority=1)
    data = todo.to_dict()
    assert "priority" in data
    assert data["priority"] == 1


def test_todo_backward_compatibility_without_priority() -> None:
    """Old data files without priority field should load correctly."""
    # Simulate loading old data that has no priority field
    old_data = {"id": 1, "text": "old task", "done": False}
    todo = Todo.from_dict(old_data)
    assert todo.priority == 0


def test_todo_priority_values() -> None:
    """Todo should support priority values -1, 0, 1."""
    low = Todo(id=1, text="low", priority=-1)
    assert low.priority == -1

    normal = Todo(id=2, text="normal", priority=0)
    assert normal.priority == 0

    high = Todo(id=3, text="high", priority=1)
    assert high.priority == 1
