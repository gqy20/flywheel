"""Tests for Todo priority field (Issue #4148).

These tests verify that:
1. Todo accepts optional priority field with default 2
2. Invalid priority raises ValueError with clear message
3. to_dict() includes priority in output
4. from_dict() reads priority with default 2 for backward compatibility
5. set_priority() updates updated_at timestamp
"""

from __future__ import annotations

import time

import pytest

from flywheel.todo import Todo


class TestTodoDefaultPriority:
    """Tests for default priority behavior."""

    def test_todo_default_priority_is_2(self) -> None:
        """Todo without explicit priority should have priority 2."""
        todo = Todo(id=1, text="test task")
        assert todo.priority == 2

    def test_todo_with_explicit_priority(self) -> None:
        """Todo should accept explicit priority value."""
        todo = Todo(id=1, text="urgent task", priority=0)
        assert todo.priority == 0

    def test_todo_priority_all_valid_values(self) -> None:
        """Todo should accept priority values 0, 1, 2, 3."""
        for prio in [0, 1, 2, 3]:
            todo = Todo(id=1, text=f"task with priority {prio}", priority=prio)
            assert todo.priority == prio


class TestTodoPriorityValidation:
    """Tests for priority validation."""

    def test_todo_priority_below_0_raises_error(self) -> None:
        """Priority below 0 should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo(id=1, text="invalid priority", priority=-1)
        assert "priority" in str(exc_info.value).lower()
        assert "0" in str(exc_info.value) and "3" in str(exc_info.value)

    def test_todo_priority_above_3_raises_error(self) -> None:
        """Priority above 3 should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo(id=1, text="invalid priority", priority=4)
        assert "priority" in str(exc_info.value).lower()
        assert "0" in str(exc_info.value) and "3" in str(exc_info.value)

    def test_todo_priority_invalid_type_raises_error(self) -> None:
        """Non-integer priority should raise ValueError."""
        with pytest.raises((ValueError, TypeError)):
            Todo(id=1, text="invalid priority", priority="high")  # type: ignore[arg-type]


class TestTodoToDictPriority:
    """Tests for to_dict() including priority."""

    def test_todo_to_dict_includes_priority(self) -> None:
        """to_dict() should include priority field."""
        todo = Todo(id=1, text="test", priority=1)
        result = todo.to_dict()

        assert "priority" in result
        assert result["priority"] == 1

    def test_todo_to_dict_includes_default_priority(self) -> None:
        """to_dict() should include default priority value."""
        todo = Todo(id=1, text="test")
        result = todo.to_dict()

        assert "priority" in result
        assert result["priority"] == 2


class TestTodoFromDictPriority:
    """Tests for from_dict() handling priority."""

    def test_todo_from_dict_reads_priority(self) -> None:
        """from_dict() should read priority from data."""
        data = {"id": 1, "text": "test", "priority": 0}
        todo = Todo.from_dict(data)
        assert todo.priority == 0

    def test_todo_from_dict_missing_priority_defaults_to_2(self) -> None:
        """from_dict() should default priority to 2 when missing."""
        data = {"id": 1, "text": "test"}
        todo = Todo.from_dict(data)
        assert todo.priority == 2

    def test_todo_from_dict_with_done_and_priority(self) -> None:
        """from_dict() should handle priority alongside other optional fields."""
        data = {"id": 1, "text": "test", "done": True, "priority": 3}
        todo = Todo.from_dict(data)
        assert todo.priority == 3
        assert todo.done is True


class TestTodoSetPriority:
    """Tests for set_priority() method."""

    def test_set_priority_updates_value(self) -> None:
        """set_priority() should update the priority value."""
        todo = Todo(id=1, text="test", priority=2)
        todo.set_priority(0)
        assert todo.priority == 0

    def test_set_priority_updates_timestamp(self) -> None:
        """set_priority() should update updated_at timestamp."""
        todo = Todo(id=1, text="test", priority=2)
        original_updated_at = todo.updated_at
        # Small delay to ensure timestamp difference
        time.sleep(0.01)
        todo.set_priority(1)
        assert todo.updated_at != original_updated_at

    def test_set_priority_validates_value(self) -> None:
        """set_priority() should validate the priority value."""
        todo = Todo(id=1, text="test", priority=2)
        with pytest.raises(ValueError):
            todo.set_priority(5)
        # Original value should be preserved after failed validation
        assert todo.priority == 2
