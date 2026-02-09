"""Tests for Todo priority field (Issue #2482).

Priority levels:
- LOW = 0
- MEDIUM = 1 (default)
- HIGH = 2
- URGENT = 3

These tests verify that:
1. Todo dataclass has a priority field that defaults to MEDIUM (1)
2. Todo.from_dict() accepts priority 0-3, rejects invalid values
3. Todo.from_dict() defaults to MEDIUM (1) when priority is missing
4. Todo.set_priority() updates both priority and updated_at timestamp
5. Todo.set_priority() validates priority is in valid range
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


# Priority level constants
LOW = 0
MEDIUM = 1
HIGH = 2
URGENT = 3


def test_todo_has_priority_field_default_to_medium() -> None:
    """Todo should have a priority field that defaults to MEDIUM (1)."""
    todo = Todo(id=1, text="test task")
    assert hasattr(todo, "priority")
    assert todo.priority == MEDIUM


def test_todo_can_be_created_with_explicit_priority() -> None:
    """Todo should accept priority parameter on construction."""
    todo_low = Todo(id=1, text="low priority task", priority=LOW)
    assert todo_low.priority == LOW

    todo_medium = Todo(id=2, text="medium priority task", priority=MEDIUM)
    assert todo_medium.priority == MEDIUM

    todo_high = Todo(id=3, text="high priority task", priority=HIGH)
    assert todo_high.priority == HIGH

    todo_urgent = Todo(id=4, text="urgent task", priority=URGENT)
    assert todo_urgent.priority == URGENT


def test_from_dict_accepts_valid_priority_values() -> None:
    """Todo.from_dict should accept priority values 0-3."""
    # LOW (0)
    todo_low = Todo.from_dict({"id": 1, "text": "low", "priority": LOW})
    assert todo_low.priority == LOW

    # MEDIUM (1)
    todo_medium = Todo.from_dict({"id": 2, "text": "medium", "priority": MEDIUM})
    assert todo_medium.priority == MEDIUM

    # HIGH (2)
    todo_high = Todo.from_dict({"id": 3, "text": "high", "priority": HIGH})
    assert todo_high.priority == HIGH

    # URGENT (3)
    todo_urgent = Todo.from_dict({"id": 4, "text": "urgent", "priority": URGENT})
    assert todo_urgent.priority == URGENT


def test_from_dict_defaults_to_medium_when_priority_missing() -> None:
    """Todo.from_dict should default to MEDIUM (1) when priority is missing."""
    todo = Todo.from_dict({"id": 1, "text": "task without priority"})
    assert todo.priority == MEDIUM


def test_from_dict_rejects_negative_priority() -> None:
    """Todo.from_dict should reject negative priority values."""
    with pytest.raises(ValueError, match=r"priority"):
        Todo.from_dict({"id": 1, "text": "task", "priority": -1})


def test_from_dict_rejects_priority_above_3() -> None:
    """Todo.from_dict should reject priority values greater than 3."""
    with pytest.raises(ValueError, match=r"priority"):
        Todo.from_dict({"id": 1, "text": "task", "priority": 4})

    with pytest.raises(ValueError, match=r"priority"):
        Todo.from_dict({"id": 1, "text": "task", "priority": 10})


def test_from_dict_rejects_invalid_priority_type() -> None:
    """Todo.from_dict should reject non-integer priority values."""
    with pytest.raises(ValueError, match=r"priority"):
        Todo.from_dict({"id": 1, "text": "task", "priority": "high"})


def test_set_priority_updates_priority_and_timestamp() -> None:
    """Todo.set_priority should update both priority and updated_at timestamp."""
    todo = Todo(id=1, text="task", priority=LOW)
    original_updated_at = todo.updated_at

    # Set to HIGH priority
    todo.set_priority(HIGH)

    assert todo.priority == HIGH
    assert todo.updated_at != original_updated_at


def test_set_priority_validates_range() -> None:
    """Todo.set_priority should validate priority is in range 0-3."""
    todo = Todo(id=1, text="task")

    with pytest.raises(ValueError, match=r"priority"):
        todo.set_priority(-1)

    with pytest.raises(ValueError, match=r"priority"):
        todo.set_priority(4)


def test_set_priority_accepts_all_valid_levels() -> None:
    """Todo.set_priority should accept all valid priority levels."""
    todo = Todo(id=1, text="task")

    todo.set_priority(LOW)
    assert todo.priority == LOW

    todo.set_priority(MEDIUM)
    assert todo.priority == MEDIUM

    todo.set_priority(HIGH)
    assert todo.priority == HIGH

    todo.set_priority(URGENT)
    assert todo.priority == URGENT


def test_to_dict_includes_priority() -> None:
    """Todo.to_dict should include the priority field."""
    todo = Todo(id=1, text="task", priority=HIGH)
    data = todo.to_dict()

    assert "priority" in data
    assert data["priority"] == HIGH
