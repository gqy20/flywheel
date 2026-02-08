"""Tests for Todo priority field (Issue #2376).

These tests verify that:
1. Todo has a priority field (int 1-4, default 2 for medium)
2. set_priority(value: int) validates range and raises ValueError if invalid
3. from_dict validates priority is 1-4, uses default 2 if missing
4. Todo.__repr__ includes priority field
5. Todo.to_dict() includes priority field
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_with_priority_1_stores_correctly() -> None:
    """Todo created with priority=1 should store and return priority=1."""
    todo = Todo(id=1, text="critical task", priority=1)
    assert todo.priority == 1


def test_todo_without_priority_defaults_to_2() -> None:
    """Todo created without priority should default to priority=2."""
    todo = Todo(id=1, text="normal task")
    assert todo.priority == 2


def test_set_priority_valid_values() -> None:
    """set_priority(1), set_priority(2), set_priority(3), set_priority(4) should work."""
    todo = Todo(id=1, text="test task")

    todo.set_priority(1)
    assert todo.priority == 1

    todo.set_priority(2)
    assert todo.priority == 2

    todo.set_priority(3)
    assert todo.priority == 3

    todo.set_priority(4)
    assert todo.priority == 4


def test_set_priority_invalid_values() -> None:
    """set_priority(0), set_priority(5), set_priority(-1) should raise ValueError."""
    todo = Todo(id=1, text="test task")

    with pytest.raises(ValueError, match="between 1 and 4"):
        todo.set_priority(0)

    with pytest.raises(ValueError, match="between 1 and 4"):
        todo.set_priority(5)

    with pytest.raises(ValueError, match="between 1 and 4"):
        todo.set_priority(-1)


def test_from_dict_with_valid_priority() -> None:
    """from_dict should accept priority 1-4."""
    for priority in [1, 2, 3, 4]:
        data = {"id": 1, "text": "task", "priority": priority}
        todo = Todo.from_dict(data)
        assert todo.priority == priority


def test_from_dict_with_missing_priority() -> None:
    """from_dict should default to priority=2 when priority is missing."""
    data = {"id": 1, "text": "task"}
    todo = Todo.from_dict(data)
    assert todo.priority == 2


def test_from_dict_with_invalid_priority() -> None:
    """from_dict should raise ValueError for priority outside 1-4."""
    data = {"id": 1, "text": "task", "priority": 5}
    with pytest.raises(ValueError, match="between 1 and 4"):
        Todo.from_dict(data)


def test_from_dict_with_zero_priority() -> None:
    """from_dict should raise ValueError for priority=0."""
    data = {"id": 1, "text": "task", "priority": 0}
    with pytest.raises(ValueError, match="between 1 and 4"):
        Todo.from_dict(data)


def test_from_dict_with_negative_priority() -> None:
    """from_dict should raise ValueError for negative priority."""
    data = {"id": 1, "text": "task", "priority": -1}
    with pytest.raises(ValueError, match="between 1 and 4"):
        Todo.from_dict(data)


def test_repr_includes_priority() -> None:
    """Todo.__repr__ should include priority field."""
    todo = Todo(id=1, text="test task", priority=1)
    result = repr(todo)
    assert "priority=1" in result


def test_to_dict_includes_priority() -> None:
    """Todo.to_dict() should include priority field."""
    todo = Todo(id=1, text="test task", priority=3)
    result = todo.to_dict()
    assert result["priority"] == 3
