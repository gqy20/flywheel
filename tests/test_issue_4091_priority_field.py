"""Tests for issue #4091: Todo priority field support."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for the priority field in Todo dataclass."""

    def test_todo_default_priority_is_zero(self) -> None:
        """Todo(id=1, text='test') should have default priority=0."""
        todo = Todo(id=1, text="test")
        assert todo.priority == 0

    def test_todo_can_set_high_priority(self) -> None:
        """Todo should accept priority=1 for high priority."""
        todo = Todo(id=1, text="urgent task", priority=1)
        assert todo.priority == 1

    def test_todo_can_set_low_priority(self) -> None:
        """Todo should accept priority=-1 for low priority."""
        todo = Todo(id=1, text="low priority task", priority=-1)
        assert todo.priority == -1

    def test_from_dict_parses_priority(self) -> None:
        """Todo.from_dict should correctly parse priority field."""
        data = {"id": 1, "text": "task", "priority": 1}
        todo = Todo.from_dict(data)
        assert todo.priority == 1

    def test_from_dict_defaults_missing_priority_to_zero(self) -> None:
        """Todo.from_dict should default missing priority to 0 for backward compatibility."""
        data = {"id": 1, "text": "old task"}
        todo = Todo.from_dict(data)
        assert todo.priority == 0

    def test_to_dict_includes_priority(self) -> None:
        """Todo.to_dict should include priority field."""
        todo = Todo(id=1, text="test", priority=1)
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 1

    def test_to_dict_includes_default_priority(self) -> None:
        """Todo.to_dict should include priority field even with default value."""
        todo = Todo(id=1, text="test")
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 0

    def test_from_dict_with_zero_priority(self) -> None:
        """Todo.from_dict should correctly parse explicit priority=0."""
        data = {"id": 1, "text": "task", "priority": 0}
        todo = Todo.from_dict(data)
        assert todo.priority == 0
