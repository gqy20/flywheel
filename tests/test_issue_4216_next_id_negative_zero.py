"""Regression tests for issue #4216: next_id does not handle negative or zero IDs.

This test suite verifies that next_id properly ignores negative and zero IDs
when computing the next available ID, preventing ID collisions and ensuring
all new IDs are positive integers.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdNegativeZeroIds:
    """Tests for next_id handling of negative and zero IDs."""

    def test_next_id_returns_1_for_empty_list(self) -> None:
        """Test that next_id returns 1 for an empty todo list."""
        storage = TodoStorage()
        assert storage.next_id([]) == 1

    def test_next_id_ignores_negative_ids(self) -> None:
        """Test that next_id ignores negative IDs when computing max."""
        storage = TodoStorage()
        # Mix of positive and negative IDs
        todos = [
            Todo(id=5, text="positive"),
            Todo(id=-3, text="negative"),
            Todo(id=0, text="zero"),
        ]
        # Should return max positive ID + 1 = 6
        assert storage.next_id(todos) == 6

    def test_next_id_returns_1_when_only_negative_ids(self) -> None:
        """Test that next_id returns 1 when list contains only negative IDs."""
        storage = TodoStorage()
        todos = [
            Todo(id=-5, text="negative 1"),
            Todo(id=-1, text="negative 2"),
        ]
        # No positive IDs, so should return 1
        assert storage.next_id(todos) == 1

    def test_next_id_returns_1_when_only_zero_id(self) -> None:
        """Test that next_id returns 1 when list contains only zero ID."""
        storage = TodoStorage()
        todos = [Todo(id=0, text="zero")]
        # Zero is not positive, should return 1
        assert storage.next_id(todos) == 1

    def test_next_id_returns_1_when_only_negative_and_zero_ids(self) -> None:
        """Test that next_id returns 1 when list contains only negative/zero IDs."""
        storage = TodoStorage()
        todos = [
            Todo(id=-10, text="negative"),
            Todo(id=0, text="zero"),
            Todo(id=-1, text="another negative"),
        ]
        # No positive IDs, should return 1
        assert storage.next_id(todos) == 1

    def test_next_id_with_positive_ids_only(self) -> None:
        """Test that next_id works correctly with only positive IDs."""
        storage = TodoStorage()
        todos = [
            Todo(id=1, text="first"),
            Todo(id=3, text="second"),
            Todo(id=5, text="third"),
        ]
        # Should return max ID + 1 = 6
        assert storage.next_id(todos) == 6

    def test_next_id_ignores_all_non_positive_keeps_positive(self) -> None:
        """Test that next_id correctly filters out all non-positive IDs."""
        storage = TodoStorage()
        todos = [
            Todo(id=-100, text="large negative"),
            Todo(id=10, text="positive"),
            Todo(id=-1, text="small negative"),
            Todo(id=0, text="zero"),
            Todo(id=5, text="another positive"),
        ]
        # Max positive is 10, so should return 11
        assert storage.next_id(todos) == 11
