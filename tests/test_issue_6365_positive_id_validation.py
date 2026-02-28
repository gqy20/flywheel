"""Tests for Todo.id positive validation (Issue #6365).

These tests verify that:
1. Todo constructor rejects id <= 0
2. Todo.from_dict rejects id <= 0
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdPositiveValidation:
    """Tests for validating that Todo.id must be a positive integer."""

    def test_todo_constructor_rejects_zero_id(self) -> None:
        """Todo constructor should reject id=0."""
        with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
            Todo(id=0, text="task")

    def test_todo_constructor_rejects_negative_id(self) -> None:
        """Todo constructor should reject negative id."""
        with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
            Todo(id=-1, text="task")

    def test_todo_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict should reject id=0."""
        with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
            Todo.from_dict({"id": 0, "text": "task"})

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict should reject negative id."""
        with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
            Todo.from_dict({"id": -1, "text": "task"})

    def test_todo_from_dict_rejects_large_negative_id(self) -> None:
        """Todo.from_dict should reject large negative id values."""
        with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
            Todo.from_dict({"id": -999, "text": "task"})

    def test_todo_constructor_accepts_positive_id(self) -> None:
        """Todo constructor should accept positive id values."""
        todo = Todo(id=1, text="task")
        assert todo.id == 1

    def test_todo_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict should accept positive id values."""
        todo = Todo.from_dict({"id": 42, "text": "task"})
        assert todo.id == 42
