"""Tests for Todo priority field (Issue #2376).

These tests verify that:
1. Todo has a priority field (int 1-4, default 2 for medium)
2. set_priority(value: int) validates range and raises ValueError if invalid
3. from_dict validates priority is 1-4, uses default 2 if missing
4. Todo.__repr__ includes priority field
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_has_priority_field() -> None:
    """Todo should have a priority field with default value of 2 (medium)."""
    todo = Todo(id=1, text="buy milk")
    assert hasattr(todo, "priority")
    assert todo.priority == 2  # default medium priority


def test_todo_priority_can_be_set() -> None:
    """Todo priority should be settable during construction."""
    todo = Todo(id=1, text="urgent task", priority=1)
    assert todo.priority == 1

    todo2 = Todo(id=2, text="low priority task", priority=4)
    assert todo2.priority == 4


def test_todo_set_priority_valid_range() -> None:
    """Todo.set_priority should accept values 1-4."""
    todo = Todo(id=1, text="test task")

    todo.set_priority(1)  # urgent
    assert todo.priority == 1

    todo.set_priority(2)  # medium
    assert todo.priority == 2

    todo.set_priority(3)  # low
    assert todo.priority == 3

    todo.set_priority(4)  # backlog
    assert todo.priority == 4


def test_todo_set_priority_invalid_range() -> None:
    """Todo.set_priority should raise ValueError for values outside 1-4."""
    todo = Todo(id=1, text="test task")

    with pytest.raises(ValueError, match="priority must be between 1 and 4"):
        todo.set_priority(0)

    with pytest.raises(ValueError, match="priority must be between 1 and 4"):
        todo.set_priority(5)

    with pytest.raises(ValueError, match="priority must be between 1 and 4"):
        todo.set_priority(-1)

    with pytest.raises(ValueError, match="priority must be between 1 and 4"):
        todo.set_priority(100)


def test_todo_set_priority_wrong_type() -> None:
    """Todo.set_priority should raise TypeError for non-integer values."""
    todo = Todo(id=1, text="test task")

    with pytest.raises(TypeError):
        todo.set_priority("high")  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        todo.set_priority(None)  # type: ignore[arg-type]


def test_todo_from_dict_with_priority() -> None:
    """Todo.from_dict should handle priority field correctly."""
    data = {"id": 1, "text": "urgent task", "priority": 1}
    todo = Todo.from_dict(data)
    assert todo.priority == 1


def test_todo_from_dict_without_priority_uses_default() -> None:
    """Todo.from_dict should use default priority of 2 when not provided."""
    data = {"id": 1, "text": "task"}
    todo = Todo.from_dict(data)
    assert todo.priority == 2


def test_todo_from_dict_invalid_priority() -> None:
    """Todo.from_dict should raise ValueError for invalid priority values."""
    data = {"id": 1, "text": "task", "priority": 0}
    with pytest.raises(ValueError, match="priority must be between 1 and 4"):
        Todo.from_dict(data)

    data = {"id": 1, "text": "task", "priority": 5}
    with pytest.raises(ValueError, match="priority must be between 1 and 4"):
        Todo.from_dict(data)


def test_todo_from_dict_wrong_priority_type() -> None:
    """Todo.from_dict should raise ValueError for non-integer priority."""
    data = {"id": 1, "text": "task", "priority": "high"}
    with pytest.raises(ValueError, match="priority must be an integer"):
        Todo.from_dict(data)


def test_todo_repr_includes_priority() -> None:
    """Todo.__repr__ should include the priority field."""
    todo = Todo(id=1, text="buy milk", priority=1)
    result = repr(todo)

    assert "priority=1" in result


def test_todo_to_dict_includes_priority() -> None:
    """Todo.to_dict should include the priority field."""
    todo = Todo(id=1, text="buy milk", priority=3)
    result = todo.to_dict()

    assert "priority" in result
    assert result["priority"] == 3


def test_todo_set_priority_updates_timestamp() -> None:
    """Todo.set_priority should update the updated_at timestamp."""
    todo = Todo(id=1, text="test task", priority=2)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp would differ
    import time

    time.sleep(0.01)

    todo.set_priority(1)

    assert todo.priority == 1
    assert todo.updated_at != original_updated_at


def test_todo_priority_values_meaning() -> None:
    """Verify priority levels: 1=urgent, 2=medium, 3=low, 4=backlog."""
    todo1 = Todo(id=1, text="urgent", priority=1)
    todo2 = Todo(id=2, text="medium", priority=2)
    todo3 = Todo(id=3, text="low", priority=3)
    todo4 = Todo(id=4, text="backlog", priority=4)

    assert todo1.priority == 1
    assert todo2.priority == 2
    assert todo3.priority == 3
    assert todo4.priority == 4
