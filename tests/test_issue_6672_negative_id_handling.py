"""Tests for negative/non-sequential ID handling (Issue #6672).

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
        with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*non-negative"):
            Todo.from_dict({"id": -1, "text": "task"})

    def test_todo_from_dict_rejects_negative_id_large(self) -> None:
        """Todo.from_dict should reject large negative IDs."""
        with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*non-negative"):
            Todo.from_dict({"id": -999, "text": "task"})

    def test_todo_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict should accept positive IDs."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.id == 1

    def test_todo_from_dict_accepts_zero_id(self) -> None:
        """Todo.from_dict should accept zero as a valid ID (edge case)."""
        # Note: The issue says validate positive integers, but 0 is non-negative
        # and the acceptance criteria specifically mentions negative IDs
        todo = Todo.from_dict({"id": 0, "text": "task"})
        assert todo.id == 0


class TestNextIdWithNegativeIds:
    """Tests for next_id behavior with negative IDs."""

    def test_next_id_returns_1_when_all_ids_are_negative(self) -> None:
        """next_id should return 1 when all existing IDs are negative."""
        storage = TodoStorage()
        todos = [Todo(id=-5, text="negative id todo")]
        # After fix, this should return 1, not -4
        assert storage.next_id(todos) == 1

    def test_next_id_returns_1_with_empty_list(self) -> None:
        """next_id should return 1 when todo list is empty."""
        storage = TodoStorage()
        assert storage.next_id([]) == 1

    def test_next_id_ignores_negative_ids(self) -> None:
        """next_id should ignore negative IDs and compute from positive ones."""
        storage = TodoStorage()
        # Mix of positive and negative IDs
        todos = [
            Todo(id=-10, text="negative"),
            Todo(id=5, text="positive"),
            Todo(id=-3, text="another negative"),
        ]
        # Should return 6 (max positive + 1), not -2 or -9
        assert storage.next_id(todos) == 6

    def test_next_id_with_zero_id(self) -> None:
        """next_id should handle zero ID correctly."""
        storage = TodoStorage()
        todos = [Todo(id=0, text="zero id")]
        # max(0) + 1 = 1
        assert storage.next_id(todos) == 1

    def test_next_id_with_sequential_positive_ids(self) -> None:
        """next_id should work correctly with normal sequential positive IDs."""
        storage = TodoStorage()
        todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
        assert storage.next_id(todos) == 3
