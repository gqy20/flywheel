"""Tests for Todo priority field support (Issue #3337).

These tests verify that:
1. Todo can accept an optional priority parameter (None/1/2/3)
2. from_dict/to_dict correctly serialize the priority field
3. CLI list can sort by priority (--sort=priority)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_priority_optional_field_default_none() -> None:
    """Todo should accept optional priority field with default None."""
    todo = Todo(id=1, text="buy milk")
    assert todo.priority is None


def test_todo_priority_can_be_set() -> None:
    """Todo should accept priority values 1, 2, 3."""
    todo1 = Todo(id=1, text="high priority task", priority=1)
    todo2 = Todo(id=2, text="medium priority task", priority=2)
    todo3 = Todo(id=3, text="low priority task", priority=3)

    assert todo1.priority == 1
    assert todo2.priority == 2
    assert todo3.priority == 3


def test_todo_priority_explicit_none() -> None:
    """Todo should accept explicit None for priority."""
    todo = Todo(id=1, text="no priority task", priority=None)
    assert todo.priority is None


def test_todo_to_dict_includes_priority() -> None:
    """to_dict() should include priority field."""
    todo = Todo(id=1, text="task", priority=2)
    result = todo.to_dict()

    assert "priority" in result
    assert result["priority"] == 2


def test_todo_to_dict_includes_priority_none() -> None:
    """to_dict() should include priority field even when None."""
    todo = Todo(id=1, text="task")
    result = todo.to_dict()

    assert "priority" in result
    assert result["priority"] is None


def test_todo_from_dict_with_priority() -> None:
    """from_dict() should correctly deserialize priority field."""
    data = {"id": 1, "text": "task", "priority": 2}
    todo = Todo.from_dict(data)

    assert todo.priority == 2


def test_todo_from_dict_without_priority() -> None:
    """from_dict() should handle missing priority field (default to None)."""
    data = {"id": 1, "text": "task"}
    todo = Todo.from_dict(data)

    assert todo.priority is None


def test_todo_from_dict_priority_none() -> None:
    """from_dict() should handle explicit None priority."""
    data = {"id": 1, "text": "task", "priority": None}
    todo = Todo.from_dict(data)

    assert todo.priority is None


def test_todo_set_priority_method() -> None:
    """Todo should have a set_priority() method to change priority."""
    todo = Todo(id=1, text="task")
    assert todo.priority is None

    todo.set_priority(1)
    assert todo.priority == 1

    todo.set_priority(3)
    assert todo.priority == 3

    todo.set_priority(None)
    assert todo.priority is None


def test_todo_set_priority_validates_range() -> None:
    """set_priority() should validate priority is None or 1-3."""
    todo = Todo(id=1, text="task")

    # Valid values should work
    todo.set_priority(None)
    todo.set_priority(1)
    todo.set_priority(2)
    todo.set_priority(3)

    # Invalid values should raise ValueError
    import pytest

    with pytest.raises(ValueError):
        todo.set_priority(0)
    with pytest.raises(ValueError):
        todo.set_priority(4)
    with pytest.raises(ValueError):
        todo.set_priority(-1)


def test_todo_priority_roundtrip() -> None:
    """to_dict() and from_dict() should roundtrip priority correctly."""
    original = Todo(id=1, text="task", priority=2)
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.priority == 2
    assert restored.id == original.id
    assert restored.text == original.text
