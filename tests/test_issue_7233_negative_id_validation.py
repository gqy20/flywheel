"""Regression tests for issue #7233: Negative ID validation.

Tests that Todo rejects negative IDs in both constructor and from_dict.
"""

import pytest

from flywheel.todo import Todo


class TestTodoNegativeIdValidation:
    """Tests for validating that Todo IDs must be non-negative."""

    def test_todo_constructor_rejects_negative_id(self) -> None:
        """Todo(id=-1, text='test') should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a non-negative integer"):
            Todo(id=-1, text="test")

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict({'id': -1, 'text': 'test'}) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a non-negative integer"):
            Todo.from_dict({"id": -1, "text": "test"})

    def test_todo_constructor_accepts_zero_id(self) -> None:
        """Todo(id=0, text='test') should work (zero is allowed)."""
        todo = Todo(id=0, text="test")
        assert todo.id == 0

    def test_todo_from_dict_accepts_zero_id(self) -> None:
        """Todo.from_dict({'id': 0, 'text': 'test'}) should work."""
        todo = Todo.from_dict({"id": 0, "text": "test"})
        assert todo.id == 0

    def test_todo_constructor_accepts_positive_id(self) -> None:
        """Todo(id=1, text='test') should work."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1
