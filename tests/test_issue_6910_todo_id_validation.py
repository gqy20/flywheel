"""Test for issue #6910: Todo ID validation for positive integers."""

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Tests for Todo id field validation."""

    def test_zero_id_raises_value_error(self) -> None:
        """Todo(id=0, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="positive integer"):
            Todo(id=0, text="test")

    def test_negative_id_raises_value_error(self) -> None:
        """Todo(id=-1, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="positive integer"):
            Todo(id=-1, text="test")

    def test_positive_id_works(self) -> None:
        """Todo(id=1, ...) should work as before."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1
        assert todo.text == "test"

    def test_from_dict_zero_id_raises_value_error(self) -> None:
        """Todo.from_dict with id=0 should raise ValueError."""
        with pytest.raises(ValueError, match="positive integer"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_from_dict_negative_id_raises_value_error(self) -> None:
        """Todo.from_dict with id=-1 should raise ValueError."""
        with pytest.raises(ValueError, match="positive integer"):
            Todo.from_dict({"id": -1, "text": "test"})

    def test_from_dict_positive_id_works(self) -> None:
        """Todo.from_dict with id=1 should work as before."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.id == 1
        assert todo.text == "test"
