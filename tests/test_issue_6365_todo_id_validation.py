"""Tests for Todo.id positive integer validation (Issue #6365).

These tests verify that:
1. Todo.id must be a positive integer (> 0)
2. Todo() constructor raises ValueError for id <= 0
3. Todo.from_dict() raises ValueError for id <= 0
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Test suite for Todo.id positive integer validation."""

    def test_todo_constructor_rejects_zero_id(self) -> None:
        """Todo(id=0, ...) should raise ValueError indicating id must be positive."""
        with pytest.raises(ValueError, match=r"id must be a positive integer"):
            Todo(id=0, text="task")

    def test_todo_constructor_rejects_negative_id(self) -> None:
        """Todo(id=-1, ...) should raise ValueError indicating id must be positive."""
        with pytest.raises(ValueError, match=r"id must be a positive integer"):
            Todo(id=-1, text="task")

    def test_todo_constructor_rejects_large_negative_id(self) -> None:
        """Todo(id=-100, ...) should raise ValueError indicating id must be positive."""
        with pytest.raises(ValueError, match=r"id must be a positive integer"):
            Todo(id=-100, text="task")

    def test_todo_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict({'id': 0, ...}) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id must be a positive integer"):
            Todo.from_dict({"id": 0, "text": "task"})

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict({'id': -1, ...}) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id must be a positive integer"):
            Todo.from_dict({"id": -1, "text": "task"})

    def test_todo_from_dict_rejects_negative_five_id(self) -> None:
        """Todo.from_dict({'id': -5, ...}) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id must be a positive integer"):
            Todo.from_dict({"id": -5, "text": "task"})

    def test_todo_constructor_accepts_positive_id(self) -> None:
        """Todo(id=1, ...) should work normally with positive id."""
        todo = Todo(id=1, text="task")
        assert todo.id == 1
        assert todo.text == "task"

    def test_todo_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict({'id': 1, ...}) should work normally with positive id."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.id == 1
        assert todo.text == "task"

    def test_todo_constructor_accepts_large_positive_id(self) -> None:
        """Todo(id=1000, ...) should work normally with large positive id."""
        todo = Todo(id=1000, text="task")
        assert todo.id == 1000
