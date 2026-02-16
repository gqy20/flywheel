"""Tests for Todo priority field (Issue #3821).

These tests verify that:
1. Todo objects can be created with a valid priority field (1-3)
2. Todo objects reject invalid priority values
3. priority field is correctly serialized/deserialized via to_dict/from_dict
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoPriority:
    """Tests for Todo priority field functionality."""

    def test_todo_accepts_valid_priority_none(self) -> None:
        """Todo should accept None as priority value."""
        todo = Todo(id=1, text="test", priority=None)
        assert todo.priority is None

    def test_todo_accepts_valid_priority_1(self) -> None:
        """Todo should accept priority 1."""
        todo = Todo(id=1, text="test", priority=1)
        assert todo.priority == 1

    def test_todo_accepts_valid_priority_2(self) -> None:
        """Todo should accept priority 2."""
        todo = Todo(id=1, text="test", priority=2)
        assert todo.priority == 2

    def test_todo_accepts_valid_priority_3(self) -> None:
        """Todo should accept priority 3."""
        todo = Todo(id=1, text="test", priority=3)
        assert todo.priority == 3

    def test_todo_default_priority_is_none(self) -> None:
        """Todo should default priority to None when not specified."""
        todo = Todo(id=1, text="test")
        assert todo.priority is None

    def test_todo_rejects_invalid_priority_zero(self) -> None:
        """Todo should reject priority value 0."""
        with pytest.raises(ValueError, match="priority"):
            Todo(id=1, text="test", priority=0)

    def test_todo_rejects_invalid_priority_four(self) -> None:
        """Todo should reject priority value 4."""
        with pytest.raises(ValueError, match="priority"):
            Todo(id=1, text="test", priority=4)

    def test_todo_rejects_invalid_priority_negative(self) -> None:
        """Todo should reject negative priority values."""
        with pytest.raises(ValueError, match="priority"):
            Todo(id=1, text="test", priority=-1)

    def test_todo_rejects_invalid_priority_string(self) -> None:
        """Todo should reject string priority values."""
        with pytest.raises(ValueError, match="priority"):
            Todo(id=1, text="test", priority="high")  # type: ignore[arg-type]

    def test_todo_priority_roundtrip_via_dict(self) -> None:
        """priority field should roundtrip correctly via to_dict/from_dict."""
        original = Todo(id=1, text="test", priority=2)
        data = original.to_dict()

        assert data["priority"] == 2

        restored = Todo.from_dict(data)
        assert restored.priority == 2

    def test_todo_priority_none_roundtrip_via_dict(self) -> None:
        """priority=None should roundtrip correctly via to_dict/from_dict."""
        original = Todo(id=1, text="test", priority=None)
        data = original.to_dict()

        assert data["priority"] is None

        restored = Todo.from_dict(data)
        assert restored.priority is None

    def test_todo_from_dict_accepts_missing_priority(self) -> None:
        """from_dict should treat missing priority as None."""
        data = {"id": 1, "text": "test"}
        todo = Todo.from_dict(data)
        assert todo.priority is None
