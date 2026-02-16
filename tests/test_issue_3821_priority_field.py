"""Tests for priority field feature (issue #3821)."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for Todo priority field functionality."""

    def test_todo_accepts_valid_priority(self) -> None:
        """Todo should accept valid priority values 1-3."""
        todo = Todo(id=1, text="test", priority=1)
        assert todo.priority == 1

        todo = Todo(id=2, text="test", priority=2)
        assert todo.priority == 2

        todo = Todo(id=3, text="test", priority=3)
        assert todo.priority == 3

    def test_todo_default_priority_is_none(self) -> None:
        """Todo should have None as default priority."""
        todo = Todo(id=1, text="test")
        assert todo.priority is None

    def test_todo_rejects_invalid_priority_zero(self) -> None:
        """Todo should reject priority=0 (valid range is 1-3)."""
        with pytest.raises(ValueError, match="priority"):
            Todo(id=1, text="test", priority=0)

    def test_todo_rejects_invalid_priority_four(self) -> None:
        """Todo should reject priority=4 (valid range is 1-3)."""
        with pytest.raises(ValueError, match="priority"):
            Todo(id=1, text="test", priority=4)

    def test_todo_rejects_invalid_priority_negative(self) -> None:
        """Todo should reject negative priority values."""
        with pytest.raises(ValueError, match="priority"):
            Todo(id=1, text="test", priority=-1)

    def test_todo_priority_roundtrip_via_dict(self) -> None:
        """Priority should survive serialization/deserialization via to_dict/from_dict."""
        original = Todo(id=1, text="test", priority=2)
        data = original.to_dict()
        assert data["priority"] == 2

        restored = Todo.from_dict(data)
        assert restored.priority == 2

    def test_todo_priority_none_roundtrip_via_dict(self) -> None:
        """None priority should survive serialization/deserialization."""
        original = Todo(id=1, text="test", priority=None)
        data = original.to_dict()
        assert data["priority"] is None

        restored = Todo.from_dict(data)
        assert restored.priority is None

    def test_from_dict_accepts_valid_priority(self) -> None:
        """from_dict should accept valid priority values."""
        todo = Todo.from_dict({"id": 1, "text": "test", "priority": 3})
        assert todo.priority == 3

    def test_from_dict_defaults_missing_priority_to_none(self) -> None:
        """from_dict should default missing priority to None."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.priority is None

    def test_from_dict_rejects_invalid_priority(self) -> None:
        """from_dict should reject invalid priority values."""
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict({"id": 1, "text": "test", "priority": 5})
