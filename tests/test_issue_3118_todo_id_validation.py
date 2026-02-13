"""Tests for Todo.id field validation (Issue #3118).

These tests verify that:
1. Todo.id must be a positive integer (id > 0)
2. Zero is rejected with clear error message
3. Negative integers are rejected with clear error message
4. Validation applies both in direct construction and from_dict()
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Tests for Todo.id validation to ensure positive integers only."""

    def test_todo_construction_rejects_zero_id(self) -> None:
        """Todo(id=0, ...) should raise ValueError indicating id must be positive."""
        with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
            Todo(id=0, text="test")

    def test_todo_construction_rejects_negative_id(self) -> None:
        """Todo(id=-1, ...) should raise ValueError indicating id must be positive."""
        with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
            Todo(id=-1, text="test")

    def test_todo_construction_accepts_positive_id(self) -> None:
        """Todo(id=1, ...) should be accepted as valid."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1

    def test_todo_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict with id=0 should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict with id=-5 should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
            Todo.from_dict({"id": -5, "text": "test"})

    def test_todo_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict with positive id should be accepted."""
        todo = Todo.from_dict({"id": 42, "text": "test"})
        assert todo.id == 42
