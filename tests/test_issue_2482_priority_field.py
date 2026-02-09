"""Tests for Issue #2482: Add priority level field to Todo model."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo

# Priority levels: LOW=0, MEDIUM=1, HIGH=2, URGENT=3
PRIORITY_LOW = 0
PRIORITY_MEDIUM = 1
PRIORITY_HIGH = 2
PRIORITY_URGENT = 3


def test_todo_has_priority_field() -> None:
    """Issue #2482: Todo should have a priority field defaulting to MEDIUM (1)."""
    todo = Todo(id=1, text="test task")
    # This will fail initially because priority field doesn't exist
    assert hasattr(todo, "priority"), "Todo should have a 'priority' field"
    assert todo.priority == PRIORITY_MEDIUM, "Default priority should be MEDIUM (1)"


def test_todo_from_dict_accepts_valid_priorities() -> None:
    """Issue #2482: Todo.from_dict() should accept priority values 0-3."""
    valid_priorities = [PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_URGENT]

    for priority in valid_priorities:
        data = {"id": 1, "text": f"task with priority {priority}", "priority": priority}
        todo = Todo.from_dict(data)
        assert todo.priority == priority, f"Priority {priority} should be preserved"


def test_todo_from_dict_defaults_to_medium() -> None:
    """Issue #2482: Todo.from_dict() should default priority to MEDIUM when not provided."""
    data = {"id": 1, "text": "task without priority"}
    todo = Todo.from_dict(data)
    assert todo.priority == PRIORITY_MEDIUM, "Missing priority should default to MEDIUM (1)"


def test_todo_from_dict_rejects_invalid_priority() -> None:
    """Issue #2482: Todo.from_dict() should reject priority values outside 0-3."""
    # Test negative values
    with pytest.raises(ValueError, match="priority"):
        Todo.from_dict({"id": 1, "text": "task", "priority": -1})

    # Test values greater than 3
    with pytest.raises(ValueError, match="priority"):
        Todo.from_dict({"id": 1, "text": "task", "priority": 4})

    with pytest.raises(ValueError, match="priority"):
        Todo.from_dict({"id": 1, "text": "task", "priority": 999})


def test_todo_set_priority_updates_field_and_timestamp() -> None:
    """Issue #2482: Todo.set_priority() should update priority and updated_at timestamp."""
    todo = Todo(id=1, text="test task")
    original_updated_at = todo.updated_at

    # This will fail initially because set_priority method doesn't exist
    assert hasattr(todo, "set_priority"), "Todo should have a 'set_priority()' method"

    todo.set_priority(PRIORITY_HIGH)
    assert todo.priority == PRIORITY_HIGH, "Priority should be updated to HIGH"
    assert todo.updated_at >= original_updated_at, "updated_at should be modified"


def test_todo_to_dict_includes_priority() -> None:
    """Issue #2482: Todo.to_dict() should include the priority field."""
    todo = Todo(id=1, text="test task", priority=PRIORITY_HIGH)
    data = todo.to_dict()

    assert "priority" in data, "to_dict() should include 'priority' field"
    assert data["priority"] == PRIORITY_HIGH, "Priority value should match"
