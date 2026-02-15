"""Tests for Todo priority field (Issue #3464)."""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_can_be_created_with_priority() -> None:
    """Todo should accept priority parameter (1=high, 2=medium, 3=low)."""
    todo = Todo(id=1, text="test task", priority=1)
    assert todo.priority == 1


def test_todo_default_priority_is_medium() -> None:
    """Todo without explicit priority should default to 2 (medium)."""
    todo = Todo(id=1, text="test task")
    assert todo.priority == 2


def test_todo_priority_values() -> None:
    """Todo should support all three priority levels."""
    todo_high = Todo(id=1, text="high", priority=1)
    todo_medium = Todo(id=2, text="medium", priority=2)
    todo_low = Todo(id=3, text="low", priority=3)

    assert todo_high.priority == 1
    assert todo_medium.priority == 2
    assert todo_low.priority == 3


def test_todo_from_dict_parses_priority() -> None:
    """from_dict should parse priority field when present."""
    todo = Todo.from_dict({"id": 1, "text": "test", "priority": 1})
    assert todo.priority == 1


def test_todo_from_dict_default_priority() -> None:
    """from_dict should default priority to 2 when not present."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.priority == 2


def test_todo_to_dict_includes_priority() -> None:
    """to_dict should include priority field."""
    todo = Todo(id=1, text="test", priority=3)
    data = todo.to_dict()

    assert "priority" in data
    assert data["priority"] == 3


def test_todo_to_dict_default_priority() -> None:
    """to_dict should include default priority value."""
    todo = Todo(id=1, text="test")
    data = todo.to_dict()

    assert data["priority"] == 2
