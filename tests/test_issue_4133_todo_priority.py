"""Tests for issue #4133: Add priority field to Todo data model."""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Test cases for the priority field in Todo dataclass."""

    def test_todo_creation_with_default_priority(self) -> None:
        """Todo should have a default priority of 0 (low)."""
        todo = Todo(id=1, text="test task")
        assert hasattr(todo, "priority")
        assert todo.priority == 0

    def test_todo_creation_with_explicit_priority(self) -> None:
        """Todo should accept explicit priority values."""
        todo_low = Todo(id=1, text="low priority task", priority=0)
        assert todo_low.priority == 0

        todo_medium = Todo(id=2, text="medium priority task", priority=1)
        assert todo_medium.priority == 1

        todo_high = Todo(id=3, text="high priority task", priority=2)
        assert todo_high.priority == 2

    def test_to_dict_includes_priority(self) -> None:
        """to_dict() should include priority in the output."""
        todo = Todo(id=1, text="test task", priority=2)
        result = todo.to_dict()

        assert "priority" in result
        assert result["priority"] == 2

    def test_to_dict_includes_default_priority(self) -> None:
        """to_dict() should include default priority value."""
        todo = Todo(id=1, text="test task")
        result = todo.to_dict()

        assert "priority" in result
        assert result["priority"] == 0

    def test_from_dict_parses_priority(self) -> None:
        """from_dict() should correctly parse priority from JSON data."""
        data = {"id": 1, "text": "test task", "priority": 1}
        todo = Todo.from_dict(data)

        assert todo.priority == 1

    def test_from_dict_handles_missing_priority(self) -> None:
        """from_dict() should use default priority when not provided."""
        data = {"id": 1, "text": "test task"}
        todo = Todo.from_dict(data)

        assert todo.priority == 0

    def test_from_dict_priority_roundtrip(self) -> None:
        """Test from_dict/to_dict roundtrip preserves priority."""
        original_data = {"id": 1, "text": "high priority task", "priority": 2}
        todo = Todo.from_dict(original_data)
        result = todo.to_dict()

        assert result["priority"] == 2

    def test_set_priority_method_exists(self) -> None:
        """Todo should have a set_priority() method."""
        todo = Todo(id=1, text="test task")
        assert hasattr(todo, "set_priority")
        assert callable(todo.set_priority)

    def test_set_priority_updates_priority(self) -> None:
        """set_priority() should update the priority value."""
        todo = Todo(id=1, text="test task", priority=0)

        todo.set_priority(2)
        assert todo.priority == 2

        todo.set_priority(1)
        assert todo.priority == 1
