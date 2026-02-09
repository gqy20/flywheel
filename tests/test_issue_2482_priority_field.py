"""Tests for Issue #2482: Add priority level field to Todo model.

Priority levels: 0=LOW, 1=MEDIUM (default), 2=HIGH, 3=URGENT
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_has_priority_field_defaulting_to_medium() -> None:
    """Issue #2482: Todo should have a priority field defaulting to MEDIUM (1)."""
    todo = Todo(id=1, text="test task")
    assert hasattr(todo, "priority"), "Todo should have a 'priority' field"
    assert todo.priority == 1, "Default priority should be MEDIUM (1)"


def test_todo_accepts_valid_priority_levels() -> None:
    """Issue #2482: Todo should accept priority levels 0-3."""
    # LOW (0)
    todo_low = Todo(id=1, text="low priority task", priority=0)
    assert todo_low.priority == 0

    # MEDIUM (1)
    todo_medium = Todo(id=2, text="medium priority task", priority=1)
    assert todo_medium.priority == 1

    # HIGH (2)
    todo_high = Todo(id=3, text="high priority task", priority=2)
    assert todo_high.priority == 2

    # URGENT (3)
    todo_urgent = Todo(id=4, text="urgent priority task", priority=3)
    assert todo_urgent.priority == 3


def test_todo_set_priority_updates_priority_and_timestamp() -> None:
    """Issue #2482: Todo.set_priority() should update both priority and updated_at."""
    todo = Todo(id=1, text="test task", priority=0)
    original_updated_at = todo.updated_at

    # Set priority to HIGH (2)
    todo.set_priority(2)
    assert todo.priority == 2
    assert todo.updated_at >= original_updated_at


def test_todo_set_priority_rejects_invalid_values() -> None:
    """Issue #2482: Todo.set_priority() should reject values outside 0-3."""
    todo = Todo(id=1, text="test task", priority=1)
    original_updated_at = todo.updated_at
    original_priority = todo.priority

    # Negative values should be rejected
    with pytest.raises(ValueError, match="priority"):
        todo.set_priority(-1)

    # Values greater than 3 should be rejected
    with pytest.raises(ValueError, match="priority"):
        todo.set_priority(4)

    # Verify state unchanged after failed validation
    assert todo.priority == original_priority
    assert todo.updated_at == original_updated_at


def test_todo_from_dict_accepts_priority_0_to_3() -> None:
    """Issue #2482: Todo.from_dict() should accept priority values 0-3."""
    # LOW (0)
    todo_low = Todo.from_dict({"id": 1, "text": "low", "priority": 0})
    assert todo_low.priority == 0

    # MEDIUM (1)
    todo_medium = Todo.from_dict({"id": 2, "text": "medium", "priority": 1})
    assert todo_medium.priority == 1

    # HIGH (2)
    todo_high = Todo.from_dict({"id": 3, "text": "high", "priority": 2})
    assert todo_high.priority == 2

    # URGENT (3)
    todo_urgent = Todo.from_dict({"id": 4, "text": "urgent", "priority": 3})
    assert todo_urgent.priority == 3


def test_todo_from_dict_defaults_priority_to_medium() -> None:
    """Issue #2482: Todo.from_dict() should default priority to 1 (MEDIUM) when not provided."""
    todo = Todo.from_dict({"id": 1, "text": "task without priority"})
    assert todo.priority == 1


def test_todo_from_dict_rejects_invalid_priority() -> None:
    """Issue #2482: Todo.from_dict() should reject priority values outside 0-3."""
    # Negative priority should be rejected
    with pytest.raises(ValueError, match="priority"):
        Todo.from_dict({"id": 1, "text": "task", "priority": -1})

    # Priority greater than 3 should be rejected
    with pytest.raises(ValueError, match="priority"):
        Todo.from_dict({"id": 1, "text": "task", "priority": 4})

    # Non-integer priority should be rejected
    with pytest.raises(ValueError, match="priority"):
        Todo.from_dict({"id": 1, "text": "task", "priority": "high"})


def test_todo_to_dict_includes_priority() -> None:
    """Issue #2482: Todo.to_dict() should include the priority field."""
    todo = Todo(id=1, text="test task", priority=2)
    todo_dict = todo.to_dict()

    assert "priority" in todo_dict
    assert todo_dict["priority"] == 2


def test_todo_to_dict_includes_default_priority() -> None:
    """Issue #2482: Todo.to_dict() should include priority even when using default."""
    todo = Todo(id=1, text="test task")
    todo_dict = todo.to_dict()

    assert "priority" in todo_dict
    assert todo_dict["priority"] == 1
