"""Tests for issue #5125: Negative ID validation.

Bug: next_id() generates negative IDs when todos contain negative IDs.
Fix: Add validation in Todo.from_dict() to reject negative IDs and
     modify next_id() to ensure positive IDs as a defensive measure.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestTodoFromDictRejectsNegativeId:
    """Tests for Todo.from_dict rejecting negative IDs."""

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict should reject negative IDs with clear error message."""
        with pytest.raises(ValueError, match="'id' must be a positive integer"):
            Todo.from_dict({"id": -1, "text": "task"})

    def test_todo_from_dict_rejects_large_negative_id(self) -> None:
        """Todo.from_dict should reject large negative IDs."""
        with pytest.raises(ValueError, match="'id' must be a positive integer"):
            Todo.from_dict({"id": -100, "text": "task"})

    def test_todo_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict should reject zero as an invalid ID."""
        with pytest.raises(ValueError, match="'id' must be a positive integer"):
            Todo.from_dict({"id": 0, "text": "task"})


class TestNextIdReturnsPositive:
    """Tests for next_id always returning positive integers."""

    def test_next_id_with_empty_list_returns_one(self) -> None:
        """next_id([]) should return 1."""
        storage = TodoStorage(":memory:")
        assert storage.next_id([]) == 1

    def test_next_id_with_positive_todos_returns_next(self) -> None:
        """next_id with normal positive IDs should return max+1."""
        storage = TodoStorage(":memory:")
        todos = [Todo(id=1, text="a"), Todo(id=5, text="b")]
        assert storage.next_id(todos) == 6

    def test_next_id_with_zero_id_todo_returns_one(self) -> None:
        """next_id with todo containing id=0 should return 1 (defense in depth)."""
        storage = TodoStorage(":memory:")
        # Note: This shouldn't happen after the from_dict fix,
        # but next_id should still be defensive
        todo_with_zero = Todo.__new__(Todo)
        todo_with_zero.id = 0
        todo_with_zero.text = "zero"
        todo_with_zero.done = False
        todo_with_zero.created_at = ""
        todo_with_zero.updated_at = ""
        assert storage.next_id([todo_with_zero]) == 1

    def test_next_id_with_negative_id_todos_returns_one(self) -> None:
        """next_id with todos containing negative IDs should return 1 (defense in depth)."""
        storage = TodoStorage(":memory:")
        # Note: These shouldn't happen after the from_dict fix,
        # but next_id should still be defensive
        todo_neg5 = Todo.__new__(Todo)
        todo_neg5.id = -5
        todo_neg5.text = "negative"
        todo_neg5.done = False
        todo_neg5.created_at = ""
        todo_neg5.updated_at = ""

        todo_neg3 = Todo.__new__(Todo)
        todo_neg3.id = -3
        todo_neg3.text = "negative2"
        todo_neg3.done = False
        todo_neg3.created_at = ""
        todo_neg3.updated_at = ""

        # Previously: max(-5, -3) + 1 = -2 (WRONG!)
        # Now: Should return 1
        assert storage.next_id([todo_neg5, todo_neg3]) == 1
