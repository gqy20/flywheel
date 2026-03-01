"""Tests for Todo priority field support (Issue #6591).

These tests verify that:
1. Todo dataclass has optional priority field with default value 0
2. set_priority() method updates priority and updated_at
3. from_dict/to_dict correctly handle priority serialization
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for Todo priority field functionality."""

    def test_todo_default_priority_is_zero(self) -> None:
        """Todo should have default priority of 0 (normal)."""
        todo = Todo(id=1, text="test task")
        assert todo.priority == 0

    def test_todo_priority_can_be_set_on_creation(self) -> None:
        """Todo priority can be specified during creation."""
        todo = Todo(id=1, text="high priority task", priority=1)
        assert todo.priority == 1

    def test_set_priority_updates_value(self) -> None:
        """set_priority() should update the priority value."""
        todo = Todo(id=1, text="test task")
        assert todo.priority == 0

        todo.set_priority(1)
        assert todo.priority == 1

    def test_set_priority_updates_updated_at(self) -> None:
        """set_priority() should update the updated_at timestamp."""
        todo = Todo(id=1, text="test task")
        original_updated_at = todo.updated_at

        # Small delay to ensure timestamp difference
        time.sleep(0.01)

        todo.set_priority(1)
        assert todo.updated_at != original_updated_at

    def test_to_dict_includes_priority(self) -> None:
        """to_dict() should include priority field."""
        todo = Todo(id=1, text="test task", priority=1)
        data = todo.to_dict()

        assert "priority" in data
        assert data["priority"] == 1

    def test_to_dict_includes_default_priority(self) -> None:
        """to_dict() should include priority field even with default value."""
        todo = Todo(id=1, text="test task")
        data = todo.to_dict()

        assert "priority" in data
        assert data["priority"] == 0

    def test_from_dict_handles_priority(self) -> None:
        """from_dict() should correctly deserialize priority field."""
        data = {"id": 1, "text": "test task", "priority": 1}
        todo = Todo.from_dict(data)

        assert todo.priority == 1

    def test_from_dict_defaults_priority_to_zero(self) -> None:
        """from_dict() should default priority to 0 if not present."""
        data = {"id": 1, "text": "test task"}
        todo = Todo.from_dict(data)

        assert todo.priority == 0

    def test_from_dict_preserves_all_fields_with_priority(self) -> None:
        """from_dict() should preserve all fields including priority."""
        data = {
            "id": 42,
            "text": "complete task",
            "done": True,
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-02T00:00:00+00:00",
            "priority": 2,
        }
        todo = Todo.from_dict(data)

        assert todo.id == 42
        assert todo.text == "complete task"
        assert todo.done is True
        assert todo.created_at == "2024-01-01T00:00:00+00:00"
        assert todo.updated_at == "2024-01-02T00:00:00+00:00"
        assert todo.priority == 2

    def test_priority_roundtrip_via_dict(self) -> None:
        """Priority should survive a to_dict/from_dict roundtrip."""
        original = Todo(id=1, text="test task", priority=1)
        data = original.to_dict()
        restored = Todo.from_dict(data)

        assert restored.priority == original.priority
