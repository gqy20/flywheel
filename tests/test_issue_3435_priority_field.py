"""Tests for issue #3435: Add priority field to Todo data model."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_has_priority_field_with_default() -> None:
    """Todo should include a priority field with a default value."""
    todo = Todo(id=1, text="test task")
    assert hasattr(todo, "priority")
    assert todo.priority == 2  # Default to medium priority


def test_todo_can_be_created_with_priority() -> None:
    """Todo should accept priority during creation."""
    todo = Todo(id=1, text="high priority task", priority=1)
    assert todo.priority == 1

    todo2 = Todo(id=2, text="low priority task", priority=3)
    assert todo2.priority == 3


def test_todo_set_priority_validates_and_updates() -> None:
    """Todo.set_priority() should validate and update priority with timestamp."""
    todo = Todo(id=1, text="test task", priority=2)
    original_updated_at = todo.updated_at

    # Valid priority change
    todo.set_priority(1)
    assert todo.priority == 1
    assert todo.updated_at >= original_updated_at


def test_todo_set_priority_rejects_invalid_values() -> None:
    """Todo.set_priority() should reject values outside 1-3 range."""
    todo = Todo(id=1, text="test task")

    with pytest.raises(ValueError, match="priority"):
        todo.set_priority(0)

    with pytest.raises(ValueError, match="priority"):
        todo.set_priority(4)

    with pytest.raises(ValueError, match="priority"):
        todo.set_priority(-1)


def test_todo_from_dict_accepts_priority() -> None:
    """Todo.from_dict() should accept optional 'priority' key."""
    # With priority specified
    data = {"id": 1, "text": "test", "priority": 1}
    todo = Todo.from_dict(data)
    assert todo.priority == 1

    # Without priority (should use default)
    data2 = {"id": 2, "text": "test2"}
    todo2 = Todo.from_dict(data2)
    assert todo2.priority == 2


def test_todo_to_dict_includes_priority() -> None:
    """Todo.to_dict() should include priority in output."""
    todo = Todo(id=1, text="test task", priority=1)
    result = todo.to_dict()

    assert "priority" in result
    assert result["priority"] == 1


def test_todo_from_dict_validates_priority() -> None:
    """Todo.from_dict() should validate priority is in valid range."""
    # Invalid priority (too low)
    with pytest.raises(ValueError, match="priority"):
        Todo.from_dict({"id": 1, "text": "test", "priority": 0})

    # Invalid priority (too high)
    with pytest.raises(ValueError, match="priority"):
        Todo.from_dict({"id": 1, "text": "test", "priority": 4})

    # Invalid priority (wrong type)
    with pytest.raises(ValueError, match="priority"):
        Todo.from_dict({"id": 1, "text": "test", "priority": "high"})


def test_priority_roundtrip_through_dict() -> None:
    """Priority should be preserved through to_dict/from_dict cycle."""
    original = Todo(id=1, text="test task", priority=1)
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.priority == original.priority == 1
