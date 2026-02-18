"""Tests for Todo priority field (Issue #4148).

These tests verify that:
1. Todo accepts optional priority field with default 2
2. Invalid priority raises ValueError with clear message
3. to_dict() includes priority in output
4. from_dict() reads priority with default 2 for backward compatibility
5. set_priority() method updates the priority and timestamp
"""

from __future__ import annotations

import time

import pytest

from flywheel.todo import Todo


class TestTodoPriorityDefault:
    """Tests for default priority behavior."""

    def test_todo_default_priority_is_2(self) -> None:
        """Todo created without priority should default to 2."""
        todo = Todo(id=1, text="a")
        assert todo.priority == 2

    def test_todo_explicit_priority_0(self) -> None:
        """Todo should accept priority 0 (highest)."""
        todo = Todo(id=1, text="urgent", priority=0)
        assert todo.priority == 0

    def test_todo_explicit_priority_3(self) -> None:
        """Todo should accept priority 3 (lowest)."""
        todo = Todo(id=1, text="low priority", priority=3)
        assert todo.priority == 3


class TestTodoPriorityValidation:
    """Tests for priority validation."""

    def test_todo_priority_below_0_raises_error(self) -> None:
        """Priority below 0 should raise ValueError."""
        with pytest.raises(ValueError, match="priority"):
            Todo(id=1, text="test", priority=-1)

    def test_todo_priority_above_3_raises_error(self) -> None:
        """Priority above 3 should raise ValueError."""
        with pytest.raises(ValueError, match="priority"):
            Todo(id=1, text="test", priority=4)

    def test_todo_priority_must_be_int(self) -> None:
        """Priority must be an integer."""
        with pytest.raises((ValueError, TypeError)):
            Todo(id=1, text="test", priority="high")  # type: ignore[arg-type]


class TestTodoToDictIncludesPriority:
    """Tests for to_dict() including priority."""

    def test_to_dict_includes_priority(self) -> None:
        """to_dict() should include priority field."""
        todo = Todo(id=1, text="test", priority=1)
        result = todo.to_dict()
        assert "priority" in result
        assert result["priority"] == 1

    def test_to_dict_includes_default_priority(self) -> None:
        """to_dict() should include priority even when using default."""
        todo = Todo(id=1, text="test")
        result = todo.to_dict()
        assert result["priority"] == 2


class TestTodoFromDictPriority:
    """Tests for from_dict() handling priority."""

    def test_from_dict_reads_priority(self) -> None:
        """from_dict() should read priority from data."""
        data = {"id": 1, "text": "test", "priority": 0}
        todo = Todo.from_dict(data)
        assert todo.priority == 0

    def test_from_dict_missing_priority_defaults_to_2(self) -> None:
        """from_dict() should default to 2 when priority is missing."""
        data = {"id": 1, "text": "test"}
        todo = Todo.from_dict(data)
        assert todo.priority == 2

    def test_from_dict_invalid_priority_raises_error(self) -> None:
        """from_dict() should validate priority range."""
        data = {"id": 1, "text": "test", "priority": 5}
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict(data)


class TestTodoSetPriority:
    """Tests for set_priority() method."""

    def test_set_priority_updates_value(self) -> None:
        """set_priority() should update the priority value."""
        todo = Todo(id=1, text="test", priority=2)
        todo.set_priority(0)
        assert todo.priority == 0

    def test_set_priority_updates_timestamp(self) -> None:
        """set_priority() should update the updated_at timestamp."""
        todo = Todo(id=1, text="test", priority=2)
        original_updated_at = todo.updated_at
        time.sleep(0.01)  # Small delay to ensure timestamp differs
        todo.set_priority(1)
        assert todo.updated_at != original_updated_at

    def test_set_priority_validates_range(self) -> None:
        """set_priority() should validate priority is in range 0-3."""
        todo = Todo(id=1, text="test", priority=2)
        with pytest.raises(ValueError, match="priority"):
            todo.set_priority(5)
        with pytest.raises(ValueError, match="priority"):
            todo.set_priority(-1)
