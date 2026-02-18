"""Tests for priority field in Todo data model (Issue #4133).

These tests verify that:
1. Todo dataclass includes priority field with default value
2. from_dict() correctly parses priority from JSON
3. to_dict() includes priority in output
4. Priority values are validated properly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for Todo priority field."""

    def test_todo_has_priority_field(self) -> None:
        """Todo should have a priority field."""
        todo = Todo(id=1, text="test task")
        # Should have priority attribute
        assert hasattr(todo, "priority")

    def test_todo_priority_default_value(self) -> None:
        """Todo priority should default to 0 (low)."""
        todo = Todo(id=1, text="test task")
        assert todo.priority == 0

    def test_todo_priority_can_be_set(self) -> None:
        """Todo priority should accept valid values (0, 1, 2)."""
        todo_low = Todo(id=1, text="low priority", priority=0)
        assert todo_low.priority == 0

        todo_medium = Todo(id=2, text="medium priority", priority=1)
        assert todo_medium.priority == 1

        todo_high = Todo(id=3, text="high priority", priority=2)
        assert todo_high.priority == 2

    def test_todo_to_dict_includes_priority(self) -> None:
        """to_dict() should include priority in output."""
        todo = Todo(id=1, text="test task", priority=2)
        data = todo.to_dict()

        assert "priority" in data
        assert data["priority"] == 2

    def test_todo_from_dict_parses_priority(self) -> None:
        """from_dict() should parse priority from JSON data."""
        data = {"id": 1, "text": "test task", "priority": 1}
        todo = Todo.from_dict(data)

        assert todo.priority == 1

    def test_todo_from_dict_priority_defaults_to_zero(self) -> None:
        """from_dict() should default priority to 0 if not present."""
        data = {"id": 1, "text": "test task"}
        todo = Todo.from_dict(data)

        assert todo.priority == 0

    def test_todo_from_dict_priority_roundtrip(self) -> None:
        """from_dict() and to_dict() should roundtrip priority correctly."""
        original_data = {"id": 42, "text": "important task", "priority": 2, "done": True}
        todo = Todo.from_dict(original_data)
        result_data = todo.to_dict()

        assert result_data["priority"] == 2
        assert result_data["id"] == 42
        assert result_data["done"] is True

    def test_todo_from_dict_validates_priority_type(self) -> None:
        """from_dict() should validate priority is an integer."""
        data = {"id": 1, "text": "test", "priority": "high"}
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict(data)

    def test_todo_from_dict_validates_priority_range(self) -> None:
        """from_dict() should validate priority is in valid range (0-2)."""
        # Invalid: negative value
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict({"id": 1, "text": "test", "priority": -1})

        # Invalid: too high
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict({"id": 1, "text": "test", "priority": 3})
