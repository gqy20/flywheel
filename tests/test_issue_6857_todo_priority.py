"""Tests for Todo priority field (Issue #6857)."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_default_priority_is_zero() -> None:
    """Todo should have a default priority of 0 (normal)."""
    todo = Todo(id=1, text="test task")
    assert todo.priority == 0


def test_todo_can_be_created_with_priority() -> None:
    """Todo can be created with explicit priority values."""
    todo_high = Todo(id=1, text="high priority task", priority=1)
    assert todo_high.priority == 1

    todo_low = Todo(id=2, text="low priority task", priority=2)
    assert todo_low.priority == 2


def test_from_dict_parses_valid_priority() -> None:
    """from_dict should correctly parse valid priority values (0, 1, 2)."""
    for priority in [0, 1, 2]:
        data = {"id": 1, "text": "test", "priority": priority}
        todo = Todo.from_dict(data)
        assert todo.priority == priority


def test_from_dict_defaults_priority_to_zero() -> None:
    """from_dict should default priority to 0 if not provided."""
    data = {"id": 1, "text": "test"}
    todo = Todo.from_dict(data)
    assert todo.priority == 0


def test_from_dict_rejects_invalid_priority_high() -> None:
    """from_dict should reject priority values outside 0-2 range (too high)."""
    data = {"id": 1, "text": "test", "priority": 3}
    with pytest.raises(ValueError, match="priority"):
        Todo.from_dict(data)


def test_from_dict_rejects_invalid_priority_negative() -> None:
    """from_dict should reject negative priority values."""
    data = {"id": 1, "text": "test", "priority": -1}
    with pytest.raises(ValueError, match="priority"):
        Todo.from_dict(data)


def test_to_dict_includes_priority() -> None:
    """to_dict should include the priority field in serialization."""
    todo = Todo(id=1, text="test", priority=1)
    result = todo.to_dict()
    assert "priority" in result
    assert result["priority"] == 1


def test_to_dict_includes_default_priority() -> None:
    """to_dict should include priority even when using default value."""
    todo = Todo(id=1, text="test")
    result = todo.to_dict()
    assert "priority" in result
    assert result["priority"] == 0
