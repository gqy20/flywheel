"""Tests for issue #6011: Todo ID validation (must be positive)."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Test that Todo constructor rejects negative and zero IDs."""

    def test_todo_constructor_rejects_negative_id(self) -> None:
        """Todo(id=-1, text='test') should raise ValueError."""
        with pytest.raises(ValueError, match="id"):
            Todo(id=-1, text="test")

    def test_todo_constructor_rejects_zero_id(self) -> None:
        """Todo(id=0, text='test') should raise ValueError."""
        with pytest.raises(ValueError, match="id"):
            Todo(id=0, text="test")

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict({'id': -1, 'text': 'test'}) should raise ValueError."""
        with pytest.raises(ValueError, match="id"):
            Todo.from_dict({"id": -1, "text": "test"})

    def test_todo_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict({'id': 0, 'text': 'test'}) should raise ValueError."""
        with pytest.raises(ValueError, match="id"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_todo_constructor_accepts_positive_id(self) -> None:
        """Todo(id=1, text='test') should still work correctly."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1
        assert todo.text == "test"

    def test_todo_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict with positive ID should work correctly."""
        todo = Todo.from_dict({"id": 42, "text": "sample"})
        assert todo.id == 42
        assert todo.text == "sample"
