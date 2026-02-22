"""Regression tests for issue #5125: next_id() generates negative IDs when todos contain negative IDs.

This test suite verifies that:
1. Todo.from_dict rejects negative IDs with clear error message
2. next_id always returns positive integer >= 1
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNegativeIdValidation:
    """Tests for Todo.from_dict rejecting negative IDs."""

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict should reject negative IDs with clear error message."""
        with pytest.raises(ValueError, match=r"'id'.*must be a positive integer"):
            Todo.from_dict({"id": -1, "text": "negative id todo"})

    def test_from_dict_rejects_large_negative_id(self) -> None:
        """Todo.from_dict should reject large negative IDs."""
        with pytest.raises(ValueError, match=r"'id'.*must be a positive integer"):
            Todo.from_dict({"id": -999, "text": "large negative id todo"})

    def test_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict should accept positive IDs."""
        todo = Todo.from_dict({"id": 1, "text": "positive id todo"})
        assert todo.id == 1

    def test_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict should reject ID of zero (IDs should start at 1)."""
        with pytest.raises(ValueError, match=r"'id'.*must be a positive integer"):
            Todo.from_dict({"id": 0, "text": "zero id todo"})


class TestNextIdAlwaysPositive:
    """Tests for next_id always returning positive integers >= 1."""

    def test_next_id_returns_1_for_empty_list(self) -> None:
        """next_id should return 1 for empty list."""
        storage = TodoStorage(":memory:")
        assert storage.next_id([]) == 1

    def test_next_id_returns_1_when_max_id_is_zero(self) -> None:
        """next_id should return 1 when the only todo has id=0 (defensive).

        This is a defensive test - if Todo.from_dict is bypassed, next_id should
        still never return 0 or negative values.
        """
        # Create a Todo with id=0 directly (bypassing from_dict validation)
        todo_with_zero_id = Todo.__new__(Todo)
        todo_with_zero_id.id = 0
        todo_with_zero_id.text = "zero id"
        todo_with_zero_id.done = False
        todo_with_zero_id.created_at = ""
        todo_with_zero_id.updated_at = ""

        storage = TodoStorage(":memory:")
        # next_id should return at least 1 even with zero id
        result = storage.next_id([todo_with_zero_id])
        assert result >= 1

    def test_next_id_handles_negative_id_defensively(self) -> None:
        """next_id should return positive value even if todo has negative id.

        This is a defensive test - if Todo.from_dict validation is bypassed,
        next_id should still never return 0 or negative values.
        """
        # Create a Todo with negative id directly (bypassing from_dict validation)
        todo_with_negative_id = Todo.__new__(Todo)
        todo_with_negative_id.id = -5
        todo_with_negative_id.text = "negative id"
        todo_with_negative_id.done = False
        todo_with_negative_id.created_at = ""
        todo_with_negative_id.updated_at = ""

        storage = TodoStorage(":memory:")
        # next_id should return at least 1 even with negative id
        result = storage.next_id([todo_with_negative_id])
        assert result >= 1

    def test_next_id_returns_correct_value_for_normal_todos(self) -> None:
        """next_id should return max_id + 1 for normal positive IDs."""
        storage = TodoStorage(":memory:")
        todos = [Todo(id=1, text="a"), Todo(id=3, text="b"), Todo(id=5, text="c")]
        assert storage.next_id(todos) == 6
