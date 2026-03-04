"""Regression tests for Issue #7233: Negative ID validation.

This test file ensures that Todo IDs are validated to reject negative values
in both the constructor and from_dict() method.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoNegativeIdValidation:
    """Tests for rejecting negative IDs in Todo construction."""

    def test_todo_constructor_rejects_negative_id(self) -> None:
        """Todo with negative id should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*non-negative"):
            Todo(id=-1, text="test")

    def test_todo_constructor_rejects_negative_large_id(self) -> None:
        """Todo with large negative id should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*non-negative"):
            Todo(id=-999999, text="test")

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict with negative id should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*non-negative"):
            Todo.from_dict({"id": -1, "text": "test"})

    def test_todo_from_dict_rejects_negative_string_id(self) -> None:
        """Todo.from_dict with negative string id should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*non-negative"):
            Todo.from_dict({"id": "-1", "text": "test"})

    def test_todo_accepts_zero_id(self) -> None:
        """Todo with id=0 should be accepted (consistent with next_id behavior).

        Note: next_id() returns 1 for empty lists, so id=0 is technically valid
        for new items in an empty system, though unusual.
        """
        todo = Todo(id=0, text="test zero id")
        assert todo.id == 0

    def test_todo_from_dict_accepts_zero_id(self) -> None:
        """Todo.from_dict with id=0 should be accepted."""
        todo = Todo.from_dict({"id": 0, "text": "test zero id"})
        assert todo.id == 0

    def test_todo_accepts_positive_id(self) -> None:
        """Todo with positive id should be accepted."""
        todo = Todo(id=1, text="test positive id")
        assert todo.id == 1

    def test_todo_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict with positive id should be accepted."""
        todo = Todo.from_dict({"id": 1, "text": "test positive id"})
        assert todo.id == 1
