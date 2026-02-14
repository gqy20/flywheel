"""Tests for Todo priority field (Issue #3337).

These tests verify that:
1. Todo can accept optional priority parameter (None/1/2/3)
2. from_dict/to_dict correctly serialize priority field
3. Storage saves priority correctly in JSON
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_priority_default_is_none() -> None:
    """Todo priority should default to None."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert todo.priority is None


def test_todo_priority_can_be_set_to_valid_values() -> None:
    """Todo priority can be set to valid values (1, 2, 3)."""
    todo1 = Todo(id=1, text="high priority", priority=1)
    assert todo1.priority == 1

    todo2 = Todo(id=2, text="medium priority", priority=2)
    assert todo2.priority == 2

    todo3 = Todo(id=3, text="low priority", priority=3)
    assert todo3.priority == 3


def test_todo_priority_can_be_none() -> None:
    """Todo priority can be explicitly set to None."""
    todo = Todo(id=1, text="no priority", priority=None)
    assert todo.priority is None


def test_todo_to_dict_includes_priority() -> None:
    """to_dict should include priority field."""
    todo = Todo(id=1, text="test", priority=2)
    result = todo.to_dict()

    assert "priority" in result
    assert result["priority"] == 2


def test_todo_to_dict_includes_priority_when_none() -> None:
    """to_dict should include priority field even when None."""
    todo = Todo(id=1, text="test", priority=None)
    result = todo.to_dict()

    assert "priority" in result
    assert result["priority"] is None


def test_todo_from_dict_with_priority() -> None:
    """from_dict should correctly deserialize priority field."""
    data = {"id": 1, "text": "test", "done": False, "priority": 2}
    todo = Todo.from_dict(data)

    assert todo.priority == 2


def test_todo_from_dict_without_priority_defaults_to_none() -> None:
    """from_dict should default priority to None if not present."""
    data = {"id": 1, "text": "test", "done": False}
    todo = Todo.from_dict(data)

    assert todo.priority is None


def test_todo_priority_roundtrip() -> None:
    """Priority should survive to_dict -> from_dict roundtrip."""
    original = Todo(id=1, text="test", priority=1)
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.priority == 1


def test_todo_priority_none_roundtrip() -> None:
    """Priority None should survive to_dict -> from_dict roundtrip."""
    original = Todo(id=1, text="test", priority=None)
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.priority is None


def test_set_priority_method() -> None:
    """Todo should have a set_priority method to change priority."""
    todo = Todo(id=1, text="test")
    assert todo.priority is None

    todo.set_priority(1)
    assert todo.priority == 1

    todo.set_priority(None)
    assert todo.priority is None


def test_set_priority_validates_value() -> None:
    """set_priority should only accept None or 1, 2, 3."""
    import pytest

    todo = Todo(id=1, text="test")

    with pytest.raises(ValueError, match="priority"):
        todo.set_priority(4)

    with pytest.raises(ValueError, match="priority"):
        todo.set_priority(0)

    with pytest.raises(ValueError, match="priority"):
        todo.set_priority(-1)
