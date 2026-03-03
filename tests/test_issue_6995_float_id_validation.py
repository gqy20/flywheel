"""Test for issue #6995: from_dict should reject float ids to prevent precision loss."""

import pytest

from flywheel.todo import Todo


class TestIssue6995FloatIdValidation:
    """Tests for float id rejection in Todo.from_dict.

    Issue: from_dict silently coerces float id to int, potentially losing precision.
    Fix: Reject float ids with a ValueError.
    """

    def test_from_dict_rejects_non_integer_float_id(self):
        """from_dict should reject float ids like 1.5 that would lose precision."""
        with pytest.raises(ValueError, match="'id' must be an integer"):
            Todo.from_dict({"id": 1.5, "text": "test"})

    def test_from_dict_rejects_integer_like_float_id(self):
        """from_dict should reject float ids even if they are integer-like (e.g., 1.0)."""
        # Even though 1.0 == 1, we reject it to enforce type strictness
        with pytest.raises(ValueError, match="'id' must be an integer"):
            Todo.from_dict({"id": 1.0, "text": "test"})

    def test_from_dict_accepts_integer_id(self):
        """from_dict should accept valid integer ids."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.id == 1

    def test_from_dict_accepts_string_integer_id(self):
        """from_dict should accept string representations of integers."""
        todo = Todo.from_dict({"id": "42", "text": "test"})
        assert todo.id == 42

    def test_from_dict_rejects_string_float_id(self):
        """from_dict should reject string representations of floats."""
        with pytest.raises(ValueError, match="'id' must be an integer"):
            Todo.from_dict({"id": "1.5", "text": "test"})
