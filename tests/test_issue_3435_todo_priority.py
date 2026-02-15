"""Tests for Todo priority field (Issue #3435).

These tests verify that:
1. Todo dataclass includes priority field with default value
2. Todo.set_priority() validates and updates priority with timestamp
3. Todo.from_dict() accepts optional 'priority' key
4. Todo.to_dict() includes priority in output
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_has_priority_field_with_default() -> None:
    """Todo should have a priority field with default value."""
    todo = Todo(id=1, text="test task")
    assert hasattr(todo, "priority")
    assert todo.priority == 2  # Default should be MEDIUM (2)


def test_todo_priority_can_be_set_on_creation() -> None:
    """Todo can be created with a specific priority."""
    todo = Todo(id=1, text="high priority task", priority=1)
    assert todo.priority == 1


def test_todo_set_priority_validates_range() -> None:
    """set_priority() should validate priority is in range 1-3."""
    todo = Todo(id=1, text="test task")

    # Valid priorities
    todo.set_priority(1)
    assert todo.priority == 1

    todo.set_priority(2)
    assert todo.priority == 2

    todo.set_priority(3)
    assert todo.priority == 3


def test_todo_set_priority_rejects_invalid_low() -> None:
    """set_priority() should reject priority < 1."""
    todo = Todo(id=1, text="test task")

    try:
        todo.set_priority(0)
        raise AssertionError("set_priority(0) should raise ValueError")
    except ValueError as e:
        assert "priority" in str(e).lower()


def test_todo_set_priority_rejects_invalid_high() -> None:
    """set_priority() should reject priority > 3."""
    todo = Todo(id=1, text="test task")

    try:
        todo.set_priority(4)
        raise AssertionError("set_priority(4) should raise ValueError")
    except ValueError as e:
        assert "priority" in str(e).lower()


def test_todo_set_priority_updates_timestamp() -> None:
    """set_priority() should update the updated_at timestamp."""
    todo = Todo(id=1, text="test task")
    original_updated_at = todo.updated_at

    todo.set_priority(1)

    assert todo.updated_at != original_updated_at


def test_todo_to_dict_includes_priority() -> None:
    """to_dict() should include priority in output."""
    todo = Todo(id=1, text="test task", priority=1)
    result = todo.to_dict()

    assert "priority" in result
    assert result["priority"] == 1


def test_todo_from_dict_accepts_priority() -> None:
    """from_dict() should accept optional 'priority' key."""
    data = {"id": 1, "text": "test task", "priority": 3}
    todo = Todo.from_dict(data)

    assert todo.priority == 3


def test_todo_from_dict_priority_defaults_to_2() -> None:
    """from_dict() should default priority to 2 if not provided."""
    data = {"id": 1, "text": "test task"}
    todo = Todo.from_dict(data)

    assert todo.priority == 2


def test_todo_from_dict_validates_priority_range() -> None:
    """from_dict() should reject invalid priority values."""
    data = {"id": 1, "text": "test task", "priority": 5}

    try:
        Todo.from_dict(data)
        raise AssertionError("from_dict with invalid priority should raise ValueError")
    except ValueError as e:
        assert "priority" in str(e).lower()
