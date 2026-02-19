"""Regression test for issue #4611: Todo id must be positive integer.

Bug: Todo constructor allows id=0 or negative id, which can cause
next_id logic issues and data consistency problems.

Acceptance criteria:
- Todo(id=0, text='test') should raise ValueError
- Todo(id=-1, text='test') should raise ValueError
- Todo(id=1, text='test') should work normally
- from_dict({'id': 0, 'text': 'test'}) should raise ValueError
"""

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Test that Todo id must be a positive integer (>= 1)."""

    def test_todo_id_zero_raises_value_error(self) -> None:
        """Todo(id=0, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo(id=0, text="test")

    def test_todo_id_negative_raises_value_error(self) -> None:
        """Todo(id=-1, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo(id=-1, text="test")

    def test_todo_id_one_works(self) -> None:
        """Todo(id=1, ...) should work normally."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1
        assert todo.text == "test"

    def test_todo_id_positive_works(self) -> None:
        """Todo with positive id should work normally."""
        todo = Todo(id=42, text="test task")
        assert todo.id == 42

    def test_from_dict_rejects_zero_id(self) -> None:
        """from_dict should reject id=0."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_from_dict_rejects_negative_id(self) -> None:
        """from_dict should reject negative id."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo.from_dict({"id": -5, "text": "test"})

    def test_from_dict_accepts_positive_id(self) -> None:
        """from_dict should accept positive id."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.id == 1
