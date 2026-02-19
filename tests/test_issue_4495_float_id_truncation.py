"""Regression test for issue #4495: from_dict silently truncates float id to int.

Bug: int(1.5) silently returns 1, causing potential data collision.
Fix: Reject float ids with non-zero decimal parts.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestFloatIdRejection:
    """Tests for rejecting float ids that would be silently truncated."""

    def test_from_dict_rejects_float_id_with_decimal(self) -> None:
        """Todo.from_dict should reject float id like 1.5 to prevent silent truncation."""
        with pytest.raises(ValueError, match="'id' must be an integer"):
            Todo.from_dict({"id": 1.5, "text": "task"})

    def test_from_dict_rejects_float_id_with_larger_decimal(self) -> None:
        """Todo.from_dict should reject float id like 2.718 to prevent silent truncation."""
        with pytest.raises(ValueError, match="'id' must be an integer"):
            Todo.from_dict({"id": 2.718, "text": "task"})

    def test_from_dict_accepts_integer_id(self) -> None:
        """Todo.from_dict should still accept integer ids."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.id == 1
        assert todo.text == "task"

    def test_from_dict_accepts_integer_string_id(self) -> None:
        """Todo.from_dict should accept string representations of integers."""
        todo = Todo.from_dict({"id": "42", "text": "task"})
        assert todo.id == 42

    def test_from_dict_rejects_float_string_id_with_decimal(self) -> None:
        """Todo.from_dict should reject string representations of floats."""
        with pytest.raises(ValueError, match="'id' must be an integer"):
            Todo.from_dict({"id": "3.14", "text": "task"})
