"""Regression tests for issue #6365: Todo.id must be positive integer.

This test ensures that Todo.id field validates against:
- Zero (id=0 should raise ValueError)
- Negative integers (id=-1 should raise ValueError)

Both direct instantiation and from_dict() should enforce this validation.
"""

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Test suite for Todo.id positive integer validation."""

    def test_direct_instantiation_with_zero_raises_value_error(self) -> None:
        """Todo(id=0, text='x') should raise ValueError."""
        with pytest.raises(ValueError, match="id must be positive"):
            Todo(id=0, text="x")

    def test_direct_instantiation_with_negative_raises_value_error(self) -> None:
        """Todo(id=-1, text='x') should raise ValueError."""
        with pytest.raises(ValueError, match="id must be positive"):
            Todo(id=-1, text="x")

    def test_from_dict_with_zero_raises_value_error(self) -> None:
        """Todo.from_dict({'id': 0, 'text': 'x'}) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be positive"):
            Todo.from_dict({"id": 0, "text": "x"})

    def test_from_dict_with_negative_raises_value_error(self) -> None:
        """Todo.from_dict({'id': -5, 'text': 'x'}) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be positive"):
            Todo.from_dict({"id": -5, "text": "x"})

    def test_from_dict_with_negative_one_raises_value_error(self) -> None:
        """Todo.from_dict({'id': -1, 'text': 'x'}) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be positive"):
            Todo.from_dict({"id": -1, "text": "x"})

    def test_positive_id_still_works(self) -> None:
        """Existing positive id tests should continue to pass."""
        todo = Todo(id=1, text="valid todo")
        assert todo.id == 1

    def test_from_dict_with_positive_id_still_works(self) -> None:
        """from_dict with positive id should still work."""
        todo = Todo.from_dict({"id": 42, "text": "valid todo"})
        assert todo.id == 42
