"""Tests for Todo priority field support (Issue #6857).

These tests verify that:
1. Todo has a priority field with default value 0
2. from_dict accepts and validates priority values (0/1/2 only)
3. to_dict includes priority in serialization
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_default_priority_is_zero() -> None:
    """Todo without explicit priority should have priority=0."""
    todo = Todo(id=1, text="task")
    assert todo.priority == 0


def test_todo_can_be_created_with_priority() -> None:
    """Todo can be created with explicit priority value."""
    todo = Todo(id=1, text="task", priority=1)
    assert todo.priority == 1


def test_todo_from_dict_accepts_valid_priority_zero() -> None:
    """from_dict should accept priority=0 (normal)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "priority": 0})
    assert todo.priority == 0


def test_todo_from_dict_accepts_valid_priority_one() -> None:
    """from_dict should accept priority=1 (high)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "priority": 1})
    assert todo.priority == 1


def test_todo_from_dict_accepts_valid_priority_two() -> None:
    """from_dict should accept priority=2 (low)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "priority": 2})
    assert todo.priority == 2


def test_todo_from_dict_defaults_priority_to_zero() -> None:
    """from_dict should default priority to 0 when not provided."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.priority == 0


def test_todo_from_dict_rejects_invalid_priority_three() -> None:
    """from_dict should reject priority=3 (invalid)."""
    with pytest.raises(ValueError, match=r"invalid.*'priority'|'priority'.*0.*1.*2"):
        Todo.from_dict({"id": 1, "text": "task", "priority": 3})


def test_todo_from_dict_rejects_invalid_priority_negative() -> None:
    """from_dict should reject negative priority values."""
    with pytest.raises(ValueError, match=r"invalid.*'priority'|'priority'.*0.*1.*2"):
        Todo.from_dict({"id": 1, "text": "task", "priority": -1})


def test_todo_from_dict_rejects_string_priority() -> None:
    """from_dict should reject string priority values."""
    with pytest.raises(ValueError, match=r"invalid.*'priority'|'priority'.*0.*1.*2"):
        Todo.from_dict({"id": 1, "text": "task", "priority": "high"})


def test_todo_to_dict_includes_priority() -> None:
    """to_dict should include priority field in output."""
    todo = Todo(id=1, text="task", priority=1)
    data = todo.to_dict()
    assert "priority" in data
    assert data["priority"] == 1


def test_todo_to_dict_includes_default_priority() -> None:
    """to_dict should include priority field even when using default."""
    todo = Todo(id=1, text="task")
    data = todo.to_dict()
    assert "priority" in data
    assert data["priority"] == 0
