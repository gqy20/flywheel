"""Tests for Todo id validation (Issue #7051).

These tests verify that:
1. Todo rejects negative id values
2. Todo rejects zero id value
3. Todo.from_dict validates id positivity
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Test suite for Todo id validation."""

    def test_todo_with_positive_id_succeeds(self) -> None:
        """Todo with positive id should be created successfully."""
        todo = Todo(id=1, text="test task")
        assert todo.id == 1

    def test_todo_with_negative_id_raises_value_error(self) -> None:
        """Todo with negative id should raise ValueError."""
        with pytest.raises(ValueError, match="id must be positive"):
            Todo(id=-1, text="test task")

    def test_todo_with_zero_id_raises_value_error(self) -> None:
        """Todo with zero id should raise ValueError."""
        with pytest.raises(ValueError, match="id must be positive"):
            Todo(id=0, text="test task")

    def test_from_dict_with_negative_id_raises_value_error(self) -> None:
        """Todo.from_dict with negative id should raise ValueError."""
        with pytest.raises(ValueError, match="id must be positive"):
            Todo.from_dict({"id": -1, "text": "test task"})

    def test_from_dict_with_zero_id_raises_value_error(self) -> None:
        """Todo.from_dict with zero id should raise ValueError."""
        with pytest.raises(ValueError, match="id must be positive"):
            Todo.from_dict({"id": 0, "text": "test task"})

    def test_from_dict_with_positive_id_succeeds(self) -> None:
        """Todo.from_dict with positive id should succeed."""
        todo = Todo.from_dict({"id": 1, "text": "test task"})
        assert todo.id == 1
