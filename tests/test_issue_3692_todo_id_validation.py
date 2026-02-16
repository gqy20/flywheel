"""Regression test for issue #3692: Todo.__init__ should reject id=0 or negative id."""

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Test that Todo id must be a positive integer."""

    def test_todo_init_rejects_zero_id(self) -> None:
        """Todo(id=0, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo(id=0, text="test")

    def test_todo_init_rejects_negative_id(self) -> None:
        """Todo(id=-1, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo(id=-1, text="test")

    def test_todo_init_accepts_positive_id(self) -> None:
        """Todo(id=1, ...) should create normally."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1
        assert todo.text == "test"
