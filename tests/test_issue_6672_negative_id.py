"""Tests for issue #6672: next_id returns incorrect ID with negative or non-sequential IDs."""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdWithNegativeIds:
    """Tests for next_id handling of negative IDs."""

    def test_next_id_with_negative_id_returns_1(self) -> None:
        """next_id should return 1 when todos contain only negative IDs.

        Bug: next_id([Todo(id=-5, text='x')]) was returning -4 instead of 1.
        """
        storage = TodoStorage()
        todos = [Todo(id=-5, text="negative id todo")]
        # The fix: next_id should return 1, not -4
        assert storage.next_id(todos) == 1

    def test_next_id_with_empty_list_returns_1(self) -> None:
        """next_id should return 1 for empty list."""
        storage = TodoStorage()
        assert storage.next_id([]) == 1

    def test_next_id_with_zero_id_returns_2(self) -> None:
        """next_id should return 2 when max ID is 0."""
        storage = TodoStorage()
        todos = [Todo(id=0, text="zero id todo")]
        assert storage.next_id(todos) == 1

    def test_next_id_with_mixed_positive_and_negative_ids(self) -> None:
        """next_id should ignore negative IDs and return max positive ID + 1."""
        storage = TodoStorage()
        todos = [
            Todo(id=-10, text="negative"),
            Todo(id=5, text="positive"),
            Todo(id=-3, text="another negative"),
        ]
        # Should return 6 (max positive ID 5 + 1), not -2 (max ID -3 + 1)
        assert storage.next_id(todos) == 6


class TestTodoFromDictNegativeIdValidation:
    """Tests for Todo.from_dict validation of negative IDs."""

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict should reject negative IDs.

        Bug: Todo.from_dict({'id': -1, 'text': 'x'}) was not raising ValueError.
        """
        with pytest.raises(ValueError, match="'id' must be a positive integer"):
            Todo.from_dict({"id": -1, "text": "negative id todo"})

    def test_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict should reject zero as an ID."""
        with pytest.raises(ValueError, match="'id' must be a positive integer"):
            Todo.from_dict({"id": 0, "text": "zero id todo"})

    def test_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict should accept positive IDs."""
        todo = Todo.from_dict({"id": 1, "text": "valid todo"})
        assert todo.id == 1

    def test_from_dict_accepts_large_positive_id(self) -> None:
        """Todo.from_dict should accept large positive IDs."""
        todo = Todo.from_dict({"id": 999999, "text": "large id todo"})
        assert todo.id == 999999
