"""Tests for Todo priority field support (Issue #6591).

These tests verify that:
1. Todo dataclass contains optional priority field with default value 0
2. set_priority() method updates priority and updated_at
3. from_dict/to_dict correctly handle priority serialization
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_default_priority_is_zero() -> None:
    """Todo should have priority=0 by default."""
    todo = Todo(id=1, text="test task")
    assert todo.priority == 0


def test_todo_priority_can_be_set_on_creation() -> None:
    """Todo should accept priority on creation."""
    todo = Todo(id=1, text="urgent task", priority=1)
    assert todo.priority == 1


def test_todo_set_priority_updates_value() -> None:
    """set_priority() should update the priority value."""
    todo = Todo(id=1, text="test task")
    assert todo.priority == 0

    todo.set_priority(1)
    assert todo.priority == 1


def test_todo_set_priority_updates_updated_at() -> None:
    """set_priority() should update updated_at timestamp."""
    todo = Todo(id=1, text="test task")
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.set_priority(2)
    assert todo.updated_at > original_updated_at


def test_todo_to_dict_includes_priority() -> None:
    """to_dict() should include priority field."""
    todo = Todo(id=1, text="test task", priority=1)
    result = todo.to_dict()

    assert "priority" in result
    assert result["priority"] == 1


def test_todo_from_dict_handles_priority() -> None:
    """from_dict() should correctly deserialize priority field."""
    data = {"id": 1, "text": "test task", "priority": 2}
    todo = Todo.from_dict(data)

    assert todo.priority == 2


def test_todo_from_dict_defaults_priority_to_zero() -> None:
    """from_dict() should default priority to 0 if not present."""
    data = {"id": 1, "text": "test task"}
    todo = Todo.from_dict(data)

    assert todo.priority == 0


def test_todo_priority_roundtrip() -> None:
    """Priority should survive to_dict/from_dict roundtrip."""
    original = Todo(id=1, text="test task", priority=3)
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.priority == original.priority
