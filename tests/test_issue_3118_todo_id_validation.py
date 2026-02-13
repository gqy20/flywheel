"""Tests for Todo.id validation (Issue #3118).

These tests verify that:
1. Todo construction with id <= 0 raises ValueError
2. Todo.from_dict with id <= 0 raises ValueError
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdValidationDirect:
    """Test direct Todo construction with invalid ids."""

    def test_todo_with_zero_id_raises_value_error(self) -> None:
        """Todo(id=0, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo(id=0, text="test")

    def test_todo_with_negative_id_raises_value_error(self) -> None:
        """Todo(id=-1, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo(id=-1, text="test")

    def test_todo_with_negative_large_id_raises_value_error(self) -> None:
        """Todo(id=-5, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo(id=-5, text="test")


class TestTodoIdValidationFromDict:
    """Test Todo.from_dict with invalid ids."""

    def test_from_dict_with_zero_id_raises_value_error(self) -> None:
        """Todo.from_dict({'id': 0, ...}) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_from_dict_with_negative_id_raises_value_error(self) -> None:
        """Todo.from_dict({'id': -1, ...}) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo.from_dict({"id": -1, "text": "test"})

    def test_from_dict_with_negative_large_id_raises_value_error(self) -> None:
        """Todo.from_dict({'id': -5, ...}) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo.from_dict({"id": -5, "text": "test"})


class TestTodoIdValidationValid:
    """Test that valid positive ids are accepted."""

    def test_todo_with_positive_id_is_valid(self) -> None:
        """Todo(id=1, ...) should be valid."""
        todo = Todo(id=1, text="valid task")
        assert todo.id == 1

    def test_todo_with_large_positive_id_is_valid(self) -> None:
        """Todo(id=1000, ...) should be valid."""
        todo = Todo(id=1000, text="valid task")
        assert todo.id == 1000

    def test_from_dict_with_positive_id_is_valid(self) -> None:
        """Todo.from_dict({'id': 1, ...}) should be valid."""
        todo = Todo.from_dict({"id": 1, "text": "valid task"})
        assert todo.id == 1
