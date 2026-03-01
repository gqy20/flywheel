"""Regression tests for issue #6521: next_id() returns incorrect ID when todos contain negative IDs.

The root cause is that Todo.from_dict() accepts negative and zero IDs, which causes
next_id() to return incorrect values (0 or negative numbers).
"""

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Test that Todo.from_dict validates ID is positive."""

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict with id=-1 should raise ValueError."""
        with pytest.raises(ValueError, match="'id' must be a positive integer"):
            Todo.from_dict({"id": -1, "text": "Test todo"})

    def test_todo_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict with id=0 should raise ValueError."""
        with pytest.raises(ValueError, match="'id' must be a positive integer"):
            Todo.from_dict({"id": 0, "text": "Test todo"})

    def test_todo_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict with id=1 should succeed."""
        todo = Todo.from_dict({"id": 1, "text": "Test todo"})
        assert todo.id == 1
        assert todo.text == "Test todo"

    def test_todo_from_dict_accepts_large_positive_id(self) -> None:
        """Todo.from_dict with a large positive id should succeed."""
        todo = Todo.from_dict({"id": 999999, "text": "Test todo"})
        assert todo.id == 999999
