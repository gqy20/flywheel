"""Regression test for issue #7106: Todo.__init__ validates id is non-negative."""

import pytest

from flywheel.todo import Todo


class TestTodoIdNonNegativeValidation:
    """Tests for Todo id non-negative validation at construction time."""

    def test_negative_id_raises_value_error(self) -> None:
        """Todo(id=-1, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            Todo(id=-1, text="test")

    def test_negative_id_minus_ten_raises_value_error(self) -> None:
        """Todo(id=-10, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            Todo(id=-10, text="another test")

    def test_zero_id_succeeds(self) -> None:
        """Todo(id=0, ...) should succeed as zero is valid."""
        todo = Todo(id=0, text="test")
        assert todo.id == 0

    def test_positive_id_succeeds(self) -> None:
        """Todo(id=1, ...) should succeed."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1

    def test_from_dict_negative_id_raises_value_error(self) -> None:
        """from_dict with negative id should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            Todo.from_dict({"id": -1, "text": "test"})

    def test_from_dict_zero_id_succeeds(self) -> None:
        """from_dict with id=0 should succeed."""
        todo = Todo.from_dict({"id": 0, "text": "test"})
        assert todo.id == 0

    def test_from_dict_positive_id_succeeds(self) -> None:
        """from_dict with positive id should succeed."""
        todo = Todo.from_dict({"id": 42, "text": "test"})
        assert todo.id == 42
