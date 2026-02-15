"""Tests for issue #3558: Validate positive IDs in from_dict and next_id.

Bug: from_dict accepts negative ID values without validation, and next_id
can return 0 when all existing IDs are negative.

Acceptance criteria:
- Todo.from_dict({'id': -1, 'text': 'x'}) should raise ValueError
- Todo.from_dict({'id': 0, 'text': 'x'}) should raise ValueError
- Todo.from_dict({'id': 1, 'text': 'x'}) should succeed
- next_id([Todo(id=-1, text='a')]) should return 1, not 0
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestTodoFromDictIdValidation:
    """Tests for Todo.from_dict ID validation."""

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict should reject negative IDs."""
        with pytest.raises(ValueError, match="'id' must be a positive integer"):
            Todo.from_dict({"id": -1, "text": "negative id"})

    def test_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict should reject zero as an ID."""
        with pytest.raises(ValueError, match="'id' must be a positive integer"):
            Todo.from_dict({"id": 0, "text": "zero id"})

    def test_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict should accept positive IDs starting from 1."""
        todo = Todo.from_dict({"id": 1, "text": "valid id"})
        assert todo.id == 1
        assert todo.text == "valid id"

    def test_from_dict_accepts_large_positive_id(self) -> None:
        """Todo.from_dict should accept large positive IDs."""
        todo = Todo.from_dict({"id": 999999, "text": "large id"})
        assert todo.id == 999999


class TestNextIdWithNegativeIds:
    """Tests for next_id behavior with invalid IDs."""

    def test_next_id_returns_1_for_empty_list(self) -> None:
        """next_id should return 1 when there are no todos."""
        storage = TodoStorage()
        assert storage.next_id([]) == 1

    def test_next_id_returns_1_when_max_id_is_negative(self) -> None:
        """next_id should return 1 if all existing IDs are negative.

        This handles the edge case where invalid IDs somehow exist in storage.
        """
        storage = TodoStorage()
        # Note: These todos would normally be rejected by from_dict,
        # but we test the next_id logic directly
        todos = [Todo(id=-5, text="negative 1"), Todo(id=-1, text="negative 2")]
        # Should return 1, not 0 (which would be max(-5, -1) + 1 = 0)
        assert storage.next_id(todos) == 1

    def test_next_id_returns_1_when_max_id_is_zero(self) -> None:
        """next_id should return 1 if the max ID is 0.

        This handles the edge case where ID 0 somehow exists in storage.
        """
        storage = TodoStorage()
        todos = [Todo(id=0, text="zero id")]
        # Should return 1, not 1 (which would be max(0) + 1 = 1)
        # Actually this is already correct, but we verify it explicitly
        assert storage.next_id(todos) == 1

    def test_next_id_returns_max_plus_one_for_valid_ids(self) -> None:
        """next_id should return max(id) + 1 for valid positive IDs."""
        storage = TodoStorage()
        todos = [Todo(id=1, text="first"), Todo(id=3, text="third"), Todo(id=2, text="second")]
        assert storage.next_id(todos) == 4
