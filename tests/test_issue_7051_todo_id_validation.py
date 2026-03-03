"""Tests for Todo id validation (Issue #7051).

These tests verify that:
1. Todo rejects negative id values with ValueError
2. Todo rejects zero id value with ValueError
3. Todo accepts positive id values
4. Todo.from_dict also validates id is positive
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Test suite for Todo id validation."""

    def test_todo_rejects_negative_id(self) -> None:
        """Todo(id=-1, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be positive"):
            Todo(id=-1, text="test")

    def test_todo_rejects_zero_id(self) -> None:
        """Todo(id=0, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be positive"):
            Todo(id=0, text="test")

    def test_todo_accepts_positive_id(self) -> None:
        """Todo(id=1, ...) should succeed."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict with negative id should raise ValueError."""
        with pytest.raises(ValueError, match="id must be positive"):
            Todo.from_dict({"id": -1, "text": "test"})

    def test_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict with zero id should raise ValueError."""
        with pytest.raises(ValueError, match="id must be positive"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict with positive id should succeed."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.id == 1
