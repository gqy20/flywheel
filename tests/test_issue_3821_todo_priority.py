"""Tests for Todo priority field (Issue #3821).

These tests verify that:
1. Todo accepts valid priority values (1-3 or None)
2. Todo rejects invalid priority values
3. Priority roundtrips correctly via to_dict/from_dict
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Test suite for Todo priority field."""

    def test_todo_accepts_valid_priority_1(self) -> None:
        """Todo should accept priority=1 (high)."""
        todo = Todo(id=1, text="high priority task", priority=1)
        assert todo.priority == 1

    def test_todo_accepts_valid_priority_2(self) -> None:
        """Todo should accept priority=2 (medium)."""
        todo = Todo(id=1, text="medium priority task", priority=2)
        assert todo.priority == 2

    def test_todo_accepts_valid_priority_3(self) -> None:
        """Todo should accept priority=3 (low)."""
        todo = Todo(id=1, text="low priority task", priority=3)
        assert todo.priority == 3

    def test_todo_accepts_none_priority(self) -> None:
        """Todo should accept priority=None (no priority set)."""
        todo = Todo(id=1, text="no priority task", priority=None)
        assert todo.priority is None

    def test_todo_default_priority_is_none(self) -> None:
        """Todo should default priority to None if not specified."""
        todo = Todo(id=1, text="task without explicit priority")
        assert todo.priority is None

    def test_todo_rejects_invalid_priority_0(self) -> None:
        """Todo should reject priority=0 (invalid)."""
        with pytest.raises(ValueError, match="priority"):
            Todo(id=1, text="task", priority=0)

    def test_todo_rejects_invalid_priority_4(self) -> None:
        """Todo should reject priority=4 (invalid)."""
        with pytest.raises(ValueError, match="priority"):
            Todo(id=1, text="task", priority=4)

    def test_todo_rejects_invalid_priority_negative(self) -> None:
        """Todo should reject negative priority values."""
        with pytest.raises(ValueError, match="priority"):
            Todo(id=1, text="task", priority=-1)

    def test_todo_rejects_invalid_priority_string(self) -> None:
        """Todo should reject string priority values."""
        with pytest.raises(ValueError, match="priority"):
            Todo(id=1, text="task", priority="high")  # type: ignore

    def test_todo_priority_roundtrip_via_dict(self) -> None:
        """Priority should roundtrip correctly via to_dict/from_dict."""
        original = Todo(id=1, text="task", priority=2)
        data = original.to_dict()
        restored = Todo.from_dict(data)

        assert restored.priority == 2
        assert restored.priority == original.priority

    def test_todo_none_priority_roundtrip_via_dict(self) -> None:
        """None priority should roundtrip correctly via to_dict/from_dict."""
        original = Todo(id=1, text="task", priority=None)
        data = original.to_dict()
        restored = Todo.from_dict(data)

        assert restored.priority is None
        assert restored.priority == original.priority

    def test_todo_priority_included_in_to_dict(self) -> None:
        """Priority field should be included in to_dict output."""
        todo = Todo(id=1, text="task", priority=1)
        data = todo.to_dict()

        assert "priority" in data
        assert data["priority"] == 1

    def test_todo_from_dict_with_priority(self) -> None:
        """Todo.from_dict should correctly parse priority field."""
        data = {"id": 1, "text": "task", "priority": 3}
        todo = Todo.from_dict(data)

        assert todo.priority == 3

    def test_todo_from_dict_without_priority(self) -> None:
        """Todo.from_dict should default to None if priority not present."""
        data = {"id": 1, "text": "task"}
        todo = Todo.from_dict(data)

        assert todo.priority is None
