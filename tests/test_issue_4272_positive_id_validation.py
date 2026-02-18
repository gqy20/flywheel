"""Regression tests for issue #4272: Validate positive id values.

Bug: No validation for negative or zero id values, allowing invalid identifiers.
Fix: Todo constructor and from_dict should raise ValueError for id <= 0.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Tests for Todo id validation - must be positive integers."""

    def test_todo_constructor_rejects_zero_id(self) -> None:
        """Bug #4272: Todo(id=0, text='test') should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo(id=0, text="test")

    def test_todo_constructor_rejects_negative_id(self) -> None:
        """Bug #4272: Todo(id=-1, text='test') should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo(id=-1, text="test")

    def test_todo_constructor_rejects_large_negative_id(self) -> None:
        """Bug #4272: Todo(id=-100, text='test') should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo(id=-100, text="test")

    def test_todo_constructor_accepts_positive_id(self) -> None:
        """Positive ids should be accepted."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1

        todo2 = Todo(id=999, text="test2")
        assert todo2.id == 999

    def test_todo_from_dict_rejects_zero_id(self) -> None:
        """Bug #4272: Todo.from_dict({'id': 0, 'text': 'test'}) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Bug #4272: Todo.from_dict({'id': -5, 'text': 'test'}) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo.from_dict({"id": -5, "text": "test"})

    def test_todo_from_dict_accepts_positive_id(self) -> None:
        """from_dict should accept positive ids."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.id == 1
