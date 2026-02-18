"""Tests for priority field in Todo model (Issue #4148).

These tests verify that:
1. Todo accepts optional priority field with default 2
2. Invalid priority (outside 0-3) raises ValueError with clear message
3. to_dict() includes priority in output
4. from_dict() reads priority with default 2 for backward compatibility
5. set_priority() method updates priority and timestamp
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoPriorityDefault:
    """Tests for default priority behavior."""

    def test_todo_default_priority_is_2(self) -> None:
        """Todo without priority should default to 2 (normal priority)."""
        todo = Todo(id=1, text="a task")
        assert todo.priority == 2

    def test_todo_can_set_priority_on_creation(self) -> None:
        """Todo should accept priority on creation."""
        todo = Todo(id=1, text="a task", priority=0)
        assert todo.priority == 0

        todo = Todo(id=2, text="another task", priority=3)
        assert todo.priority == 3


class TestTodoPriorityValidation:
    """Tests for priority validation."""

    def test_todo_priority_validation_rejects_negative(self) -> None:
        """Priority below 0 should raise ValueError."""
        with pytest.raises(ValueError, match=r"priority|must be between 0 and 3"):
            Todo(id=1, text="task", priority=-1)

    def test_todo_priority_validation_rejects_above_3(self) -> None:
        """Priority above 3 should raise ValueError."""
        with pytest.raises(ValueError, match=r"priority|must be between 0 and 3"):
            Todo(id=1, text="task", priority=4)

    def test_todo_priority_validation_rejects_large_value(self) -> None:
        """Priority above 3 should raise ValueError even for large values."""
        with pytest.raises(ValueError, match=r"priority|must be between 0 and 3"):
            Todo(id=1, text="task", priority=100)


class TestTodoPriorityToDict:
    """Tests for priority in to_dict serialization."""

    def test_todo_to_dict_includes_priority(self) -> None:
        """to_dict() should include priority field."""
        todo = Todo(id=1, text="task", priority=1)
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 1

    def test_todo_to_dict_includes_default_priority(self) -> None:
        """to_dict() should include default priority value."""
        todo = Todo(id=1, text="task")
        data = todo.to_dict()
        assert data["priority"] == 2


class TestTodoPriorityFromDict:
    """Tests for priority in from_dict deserialization."""

    def test_todo_from_dict_reads_priority(self) -> None:
        """from_dict() should read priority from data."""
        todo = Todo.from_dict({"id": 1, "text": "task", "priority": 0})
        assert todo.priority == 0

    def test_todo_from_dict_missing_priority_defaults_to_2(self) -> None:
        """from_dict() should default priority to 2 for backward compatibility."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.priority == 2

    def test_todo_from_dict_validates_priority_range(self) -> None:
        """from_dict() should validate priority is in range 0-3."""
        with pytest.raises(ValueError, match=r"priority|must be between 0 and 3"):
            Todo.from_dict({"id": 1, "text": "task", "priority": 5})

    def test_todo_from_dict_validates_priority_type(self) -> None:
        """from_dict() should validate priority is an integer."""
        with pytest.raises(ValueError, match=r"priority|must be.*integer"):
            Todo.from_dict({"id": 1, "text": "task", "priority": "high"})


class TestTodoSetPriority:
    """Tests for set_priority() method."""

    def test_todo_set_priority_updates_value(self) -> None:
        """set_priority() should update the priority value."""
        todo = Todo(id=1, text="task", priority=2)
        todo.set_priority(0)
        assert todo.priority == 0

    def test_todo_set_priority_updates_timestamp(self) -> None:
        """set_priority() should update updated_at timestamp."""
        todo = Todo(id=1, text="task", priority=2)
        original_updated_at = todo.updated_at
        todo.set_priority(1)
        assert todo.updated_at != original_updated_at

    def test_todo_set_priority_validates_range(self) -> None:
        """set_priority() should validate priority is in range 0-3."""
        todo = Todo(id=1, text="task", priority=2)
        with pytest.raises(ValueError, match=r"priority|must be between 0 and 3"):
            todo.set_priority(5)

    def test_todo_set_priority_rejects_negative(self) -> None:
        """set_priority() should reject negative values."""
        todo = Todo(id=1, text="task", priority=2)
        with pytest.raises(ValueError, match=r"priority|must be between 0 and 3"):
            todo.set_priority(-1)
