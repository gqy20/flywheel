"""Tests for Todo priority field (Issue #6591).

These tests verify that:
1. Todo dataclass contains optional priority field, defaulting to 0
2. from_dict/to_dict correctly handle priority field
3. set_priority() method updates value and updated_at
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for the priority field on Todo dataclass."""

    def test_todo_default_priority_is_zero(self) -> None:
        """Todo should have default priority=0."""
        todo = Todo(id=1, text="test task")
        assert todo.priority == 0

    def test_todo_can_be_created_with_priority(self) -> None:
        """Todo should accept priority during construction."""
        todo = Todo(id=1, text="urgent task", priority=1)
        assert todo.priority == 1

    def test_todo_priority_field_optional(self) -> None:
        """Priority field should be optional with default value."""
        todo = Todo(id=1, text="task", done=True, priority=2)
        assert todo.priority == 2

    def test_todo_high_priority(self) -> None:
        """Todo can have high priority (1)."""
        todo = Todo(id=1, text="high priority task", priority=1)
        assert todo.priority == 1


class TestTodoSetPriority:
    """Tests for the set_priority() method."""

    def test_set_priority_updates_value(self) -> None:
        """set_priority() should update the priority value."""
        todo = Todo(id=1, text="task")
        original_updated_at = todo.updated_at

        todo.set_priority(1)
        assert todo.priority == 1

    def test_set_priority_updates_updated_at(self) -> None:
        """set_priority() should update updated_at timestamp."""
        todo = Todo(id=1, text="task")
        original_updated_at = todo.updated_at

        todo.set_priority(2)
        assert todo.updated_at >= original_updated_at

    def test_set_priority_to_zero(self) -> None:
        """set_priority() should allow setting priority back to 0."""
        todo = Todo(id=1, text="task", priority=1)
        todo.set_priority(0)
        assert todo.priority == 0


class TestTodoPrioritySerialization:
    """Tests for from_dict/to_dict with priority field."""

    def test_to_dict_includes_priority(self) -> None:
        """to_dict() should include priority field."""
        todo = Todo(id=1, text="task", priority=1)
        data = todo.to_dict()

        assert "priority" in data
        assert data["priority"] == 1

    def test_to_dict_includes_default_priority(self) -> None:
        """to_dict() should include priority field even when default."""
        todo = Todo(id=1, text="task")
        data = todo.to_dict()

        assert "priority" in data
        assert data["priority"] == 0

    def test_from_dict_loads_priority(self) -> None:
        """from_dict() should load priority from data."""
        data = {"id": 1, "text": "task", "priority": 1}
        todo = Todo.from_dict(data)
        assert todo.priority == 1

    def test_from_dict_defaults_priority_to_zero(self) -> None:
        """from_dict() should default priority to 0 if not present."""
        data = {"id": 1, "text": "task"}
        todo = Todo.from_dict(data)
        assert todo.priority == 0

    def test_from_dict_validates_priority_is_int(self) -> None:
        """from_dict() should validate priority is an integer."""
        data = {"id": 1, "text": "task", "priority": "high"}
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict(data)

    def test_from_dict_validates_priority_not_negative(self) -> None:
        """from_dict() should reject negative priority values."""
        data = {"id": 1, "text": "task", "priority": -1}
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict(data)

    def test_roundtrip_preserves_priority(self) -> None:
        """Roundtrip through to_dict/from_dict should preserve priority."""
        original = Todo(id=1, text="task", priority=1)
        data = original.to_dict()
        loaded = Todo.from_dict(data)
        assert loaded.priority == original.priority
