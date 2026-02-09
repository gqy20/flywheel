"""Tests for issue #2414: next_id() generates invalid ID (0) when todos contain negative IDs.

This test file validates:
1. Loading JSON with negative ID raises ValueError
2. Loading JSON with zero ID raises ValueError
3. next_id() still works correctly with normal positive IDs
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestNegativeIdValidation:
    """Bug #2414: Todo.from_dict() should reject negative or zero IDs."""

    def test_from_dict_rejects_negative_id(self) -> None:
        """Loading JSON with id=-1 should raise ValueError."""
        data = {"id": -1, "text": "test"}

        with pytest.raises(ValueError, match="must be a positive integer"):
            Todo.from_dict(data)

    def test_from_dict_rejects_zero_id(self) -> None:
        """Loading JSON with id=0 should raise ValueError."""
        data = {"id": 0, "text": "test"}

        with pytest.raises(ValueError, match="must be a positive integer"):
            Todo.from_dict(data)

    def test_from_dict_accepts_positive_id(self) -> None:
        """Loading JSON with positive ID should still work."""
        data = {"id": 1, "text": "test"}
        todo = Todo.from_dict(data)

        assert todo.id == 1
        assert todo.text == "test"

    def test_from_dict_accepts_large_positive_id(self) -> None:
        """Loading JSON with large positive ID should work."""
        data = {"id": 999999, "text": "large id"}
        todo = Todo.from_dict(data)

        assert todo.id == 999999
