"""Tests for priority field in Todo data model.

Issue #4133: Add priority field to Todo data model
- Todo dataclass includes priority field with default value
- from_dict() correctly parses priority from JSON
- to_dict() includes priority in output
- set_priority() method to change priority
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Test suite for Todo priority field functionality."""

    def test_todo_has_priority_field_with_default_value(self) -> None:
        """Todo should have a priority field with default value 0."""
        todo = Todo(id=1, text="test task")
        assert hasattr(todo, "priority")
        assert todo.priority == 0

    def test_todo_creation_with_explicit_priority(self) -> None:
        """Todo should accept priority as a constructor argument."""
        todo = Todo(id=1, text="high priority task", priority=2)
        assert todo.priority == 2

    def test_todo_priority_values(self) -> None:
        """Todo priority should support 0=low, 1=medium, 2=high."""
        low = Todo(id=1, text="low", priority=0)
        medium = Todo(id=2, text="medium", priority=1)
        high = Todo(id=3, text="high", priority=2)

        assert low.priority == 0
        assert medium.priority == 1
        assert high.priority == 2

    def test_to_dict_includes_priority(self) -> None:
        """to_dict() should include priority in output."""
        todo = Todo(id=1, text="test", priority=2)
        data = todo.to_dict()

        assert "priority" in data
        assert data["priority"] == 2

    def test_to_dict_includes_default_priority(self) -> None:
        """to_dict() should include default priority when not specified."""
        todo = Todo(id=1, text="test")
        data = todo.to_dict()

        assert "priority" in data
        assert data["priority"] == 0

    def test_from_dict_parses_priority(self) -> None:
        """from_dict() should correctly parse priority from JSON data."""
        data = {"id": 1, "text": "test task", "priority": 2}
        todo = Todo.from_dict(data)

        assert todo.priority == 2

    def test_from_dict_defaults_priority_to_zero(self) -> None:
        """from_dict() should default priority to 0 if not present."""
        data = {"id": 1, "text": "test task"}
        todo = Todo.from_dict(data)

        assert todo.priority == 0

    def test_from_dict_validates_priority_is_integer(self) -> None:
        """from_dict() should validate priority is an integer."""
        data = {"id": 1, "text": "test", "priority": "high"}
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict(data)

    def test_from_dict_validates_priority_in_valid_range(self) -> None:
        """from_dict() should validate priority is in valid range (0-2)."""
        data = {"id": 1, "text": "test", "priority": 5}
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict(data)

    def test_set_priority_method_exists(self) -> None:
        """Todo should have a set_priority() method."""
        todo = Todo(id=1, text="test")
        assert hasattr(todo, "set_priority")
        assert callable(todo.set_priority)

    def test_set_priority_updates_priority(self) -> None:
        """set_priority() should update the priority field."""
        todo = Todo(id=1, text="test", priority=0)
        todo.set_priority(2)
        assert todo.priority == 2

    def test_set_priority_updates_updated_at(self) -> None:
        """set_priority() should update the updated_at timestamp."""
        todo = Todo(id=1, text="test", priority=0)
        original_updated_at = todo.updated_at

        todo.set_priority(2)
        assert todo.updated_at >= original_updated_at

    def test_set_priority_validates_range(self) -> None:
        """set_priority() should validate priority is in valid range."""
        todo = Todo(id=1, text="test")

        with pytest.raises(ValueError, match="priority"):
            todo.set_priority(-1)

        with pytest.raises(ValueError, match="priority"):
            todo.set_priority(3)

    def test_roundtrip_preserves_priority(self) -> None:
        """Priority should survive to_dict/from_dict roundtrip."""
        original = Todo(id=1, text="test", priority=2)
        data = original.to_dict()
        restored = Todo.from_dict(data)

        assert restored.priority == original.priority


class TestTodoPriorityStorageIntegration:
    """Integration tests for priority with storage."""

    def test_storage_saves_and_loads_priority(self, tmp_path) -> None:
        """Storage should correctly save and load todos with priority."""
        from flywheel.storage import TodoStorage

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="low priority", priority=0),
            Todo(id=2, text="medium priority", priority=1),
            Todo(id=3, text="high priority", priority=2),
        ]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 3
        assert loaded[0].priority == 0
        assert loaded[1].priority == 1
        assert loaded[2].priority == 2
