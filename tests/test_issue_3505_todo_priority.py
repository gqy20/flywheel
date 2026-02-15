"""Tests for Todo priority field (Issue #3505).

These tests verify that:
1. Todo supports optional priority field with default value 1 (medium)
2. from_dict parses priority field and validates value is 0/1/2
3. to_dict includes priority field
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Test cases for Todo priority field."""

    def test_todo_with_priority_field(self) -> None:
        """Todo should accept priority field on creation."""
        todo = Todo(id=1, text="high priority task", priority=0)
        assert todo.id == 1
        assert todo.text == "high priority task"
        assert todo.priority == 0

    def test_todo_default_priority_is_one(self) -> None:
        """Todo should default priority to 1 (medium)."""
        todo = Todo(id=1, text="task")
        assert todo.priority == 1

    def test_todo_priority_values(self) -> None:
        """Todo should accept priority values 0, 1, 2."""
        todo_low = Todo(id=1, text="low", priority=2)
        todo_med = Todo(id=2, text="medium", priority=1)
        todo_high = Todo(id=3, text="high", priority=0)

        assert todo_low.priority == 2
        assert todo_med.priority == 1
        assert todo_high.priority == 0

    def test_todo_to_dict_includes_priority(self) -> None:
        """to_dict should include priority field."""
        todo = Todo(id=1, text="task", priority=0)
        result = todo.to_dict()

        assert "priority" in result
        assert result["priority"] == 0

    def test_todo_to_dict_includes_default_priority(self) -> None:
        """to_dict should include default priority value."""
        todo = Todo(id=1, text="task")
        result = todo.to_dict()

        assert "priority" in result
        assert result["priority"] == 1

    def test_from_dict_with_priority_zero(self) -> None:
        """from_dict should parse priority=0 correctly."""
        todo = Todo.from_dict({"id": 1, "text": "high task", "priority": 0})
        assert todo.priority == 0

    def test_from_dict_with_priority_one(self) -> None:
        """from_dict should parse priority=1 correctly."""
        todo = Todo.from_dict({"id": 1, "text": "medium task", "priority": 1})
        assert todo.priority == 1

    def test_from_dict_with_priority_two(self) -> None:
        """from_dict should parse priority=2 correctly."""
        todo = Todo.from_dict({"id": 1, "text": "low task", "priority": 2})
        assert todo.priority == 2

    def test_from_dict_defaults_priority_to_one(self) -> None:
        """from_dict should default priority to 1 if not specified."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.priority == 1

    def test_from_dict_invalid_priority_too_high(self) -> None:
        """from_dict should raise ValueError for priority > 2."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": 1, "text": "task", "priority": 3})

        assert "priority" in str(exc_info.value).lower()

    def test_from_dict_invalid_priority_negative(self) -> None:
        """from_dict should raise ValueError for negative priority."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": 1, "text": "task", "priority": -1})

        assert "priority" in str(exc_info.value).lower()

    def test_from_dict_invalid_priority_five(self) -> None:
        """from_dict should raise ValueError for priority=5."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": 1, "text": "task", "priority": 5})

        assert "priority" in str(exc_info.value).lower()

    def test_from_dict_with_all_fields_including_priority(self) -> None:
        """from_dict should parse all fields including priority."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "complete task",
            "done": True,
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-02T00:00:00+00:00",
            "priority": 0,
        })

        assert todo.id == 1
        assert todo.text == "complete task"
        assert todo.done is True
        assert todo.priority == 0
        assert todo.created_at == "2024-01-01T00:00:00+00:00"
        assert todo.updated_at == "2024-01-02T00:00:00+00:00"

    def test_round_trip_preserves_priority(self) -> None:
        """to_dict and from_dict should preserve priority value."""
        original = Todo(id=1, text="task", priority=0)
        data = original.to_dict()
        restored = Todo.from_dict(data)

        assert restored.priority == original.priority
