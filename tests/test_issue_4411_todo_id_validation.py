"""Tests for Todo ID validation (Issue #4411).

These tests verify that:
1. Todo constructor raises ValueError for id <= 0
2. Todo.from_dict raises ValueError for id <= 0
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Tests for validating that Todo IDs must be positive integers."""

    def test_todo_constructor_rejects_id_zero(self) -> None:
        """Todo(id=0, text='x') should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo(id=0, text="test task")

    def test_todo_constructor_rejects_negative_id(self) -> None:
        """Todo(id=-1, text='x') should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo(id=-1, text="test task")

    def test_todo_constructor_accepts_positive_id(self) -> None:
        """Todo(id=1, text='x') should work normally."""
        todo = Todo(id=1, text="valid task")
        assert todo.id == 1

    def test_from_dict_rejects_id_zero(self) -> None:
        """Todo.from_dict({'id': 0, 'text': 'x'}) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo.from_dict({"id": 0, "text": "test task"})

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict({'id': -1, 'text': 'x'}) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo.from_dict({"id": -1, "text": "test task"})

    def test_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict with valid positive id should work normally."""
        todo = Todo.from_dict({"id": 1, "text": "valid task"})
        assert todo.id == 1
