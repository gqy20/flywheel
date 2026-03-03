"""Regression tests for issue #6910: Todo ID validation.

Ensure Todo IDs are positive integers to avoid confusion with storage.next_id()
which starts from 1.
"""

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Tests for Todo ID validation."""

    def test_zero_id_raises_value_error(self) -> None:
        """Todo with id=0 should raise ValueError."""
        with pytest.raises(ValueError, match="positive integer"):
            Todo(id=0, text="test")

    def test_negative_id_raises_value_error(self) -> None:
        """Todo with negative id should raise ValueError."""
        with pytest.raises(ValueError, match="positive integer"):
            Todo(id=-1, text="test")

    def test_positive_id_works(self) -> None:
        """Todo with positive id should work as expected."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1
        assert todo.text == "test"

    def test_from_dict_zero_id_raises_value_error(self) -> None:
        """Todo.from_dict with id=0 should raise ValueError."""
        with pytest.raises(ValueError, match="positive integer"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_from_dict_negative_id_raises_value_error(self) -> None:
        """Todo.from_dict with negative id should raise ValueError."""
        with pytest.raises(ValueError, match="positive integer"):
            Todo.from_dict({"id": -1, "text": "test"})

    def test_from_dict_positive_id_works(self) -> None:
        """Todo.from_dict with positive id should work as expected."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.id == 1
        assert todo.text == "test"
