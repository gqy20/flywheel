"""Test for issue #7065: Todo.from_dict should validate that id is a positive integer."""

import pytest

from flywheel.todo import Todo


class TestTodoFromDictIdValidation:
    """Tests for Todo.from_dict id validation (issue #7065)."""

    def test_from_dict_rejects_zero_id(self):
        """Todo.from_dict should reject id=0 with ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": 0, "text": "test"})
        assert "positive integer" in str(exc_info.value)

    def test_from_dict_rejects_negative_id(self):
        """Todo.from_dict should reject negative id with ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": -1, "text": "test"})
        assert "positive integer" in str(exc_info.value)

    def test_from_dict_rejects_negative_id_minus_five(self):
        """Todo.from_dict should reject id=-5 with ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": -5, "text": "test"})
        assert "positive integer" in str(exc_info.value)

    def test_from_dict_accepts_positive_id(self):
        """Todo.from_dict should accept id=1 as valid."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.id == 1
        assert todo.text == "test"

    def test_from_dict_accepts_larger_positive_id(self):
        """Todo.from_dict should accept larger positive ids."""
        todo = Todo.from_dict({"id": 100, "text": "another test"})
        assert todo.id == 100
        assert todo.text == "another test"
