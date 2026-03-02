"""Tests for negative and non-sequential ID handling (Issue #6672).

These tests verify that:
1. Todo.from_dict rejects negative IDs
2. next_id returns 1 when all existing IDs are negative
3. next_id handles empty list correctly
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNegativeIdValidation:
    """Tests for validating that todo IDs must be positive integers."""

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict should reject negative IDs."""
        with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*positive|'id'.*must"):
            Todo.from_dict({"id": -1, "text": "task"})

    def test_todo_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict should reject zero as an ID (IDs should be positive)."""
        with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*positive|'id'.*must"):
            Todo.from_dict({"id": 0, "text": "task"})

    def test_todo_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict should accept positive IDs."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.id == 1

        todo2 = Todo.from_dict({"id": 999, "text": "task2"})
        assert todo2.id == 999


class TestNextIdWithNegativeIds:
    """Tests for next_id behavior with edge cases."""

    def test_next_id_returns_1_for_empty_list(self) -> None:
        """next_id([]) should return 1."""
        storage = TodoStorage()
        result = storage.next_id([])
        assert result == 1

    def test_next_id_returns_1_when_all_ids_negative(self) -> None:
        """next_id should return 1 when all existing IDs are negative.

        This test will fail before the fix because the current implementation
        returns max(negative_ids) + 1 = -4 for [-5].
        """
        storage = TodoStorage()
        # Note: This test assumes Todo objects with negative IDs can be created
        # directly (which they can via Todo(id=-5, text='x'))
        # After the fix, such todos should not be loadable from storage,
        # but we test the next_id logic in isolation
        todos = [Todo(id=-5, text="x"), Todo(id=-10, text="y")]
        result = storage.next_id(todos)
        # Should return 1, not max(-5, -10) + 1 = -4
        assert result == 1

    def test_next_id_returns_1_when_all_ids_zero_or_negative(self) -> None:
        """next_id should return 1 when all existing IDs are <= 0."""
        storage = TodoStorage()
        todos = [Todo(id=0, text="x"), Todo(id=-5, text="y")]
        result = storage.next_id(todos)
        assert result == 1

    def test_next_id_with_sequential_ids(self) -> None:
        """next_id should return max + 1 for sequential positive IDs."""
        storage = TodoStorage()
        todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]
        result = storage.next_id(todos)
        assert result == 4

    def test_next_id_with_non_sequential_ids(self) -> None:
        """next_id should return max + 1 for non-sequential positive IDs."""
        storage = TodoStorage()
        todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=10, text="c")]
        result = storage.next_id(todos)
        assert result == 11
