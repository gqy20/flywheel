"""Tests for Todo ID validation (Issue #4411).

These tests verify that:
1. Todo constructor rejects id=0
2. Todo constructor rejects negative IDs
3. Todo.from_dict rejects id=0
4. Todo.from_dict rejects negative IDs
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Test suite for Todo ID validation."""

    def test_todo_constructor_rejects_zero_id(self) -> None:
        """Todo(id=0, ...) should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo(id=0, text="test")
        assert "id" in str(exc_info.value).lower()
        assert "positive" in str(exc_info.value).lower() or "greater than 0" in str(exc_info.value).lower()

    def test_todo_constructor_rejects_negative_id(self) -> None:
        """Todo(id=-1, ...) should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo(id=-1, text="test")
        assert "id" in str(exc_info.value).lower()
        assert "positive" in str(exc_info.value).lower() or "greater than 0" in str(exc_info.value).lower()

    def test_todo_constructor_accepts_positive_id(self) -> None:
        """Todo(id=1, ...) should work correctly."""
        todo = Todo(id=1, text="valid task")
        assert todo.id == 1

    def test_todo_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict({'id': 0, ...}) should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": 0, "text": "test"})
        assert "id" in str(exc_info.value).lower()
        assert "positive" in str(exc_info.value).lower() or "greater than 0" in str(exc_info.value).lower()

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict({'id': -1, ...}) should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": -1, "text": "test"})
        assert "id" in str(exc_info.value).lower()
        assert "positive" in str(exc_info.value).lower() or "greater than 0" in str(exc_info.value).lower()

    def test_todo_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict({'id': 1, ...}) should work correctly."""
        todo = Todo.from_dict({"id": 1, "text": "valid task"})
        assert todo.id == 1

    def test_todo_from_dict_with_large_negative_id(self) -> None:
        """Todo.from_dict with large negative ID should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": -999, "text": "test"})
        assert "id" in str(exc_info.value).lower()
