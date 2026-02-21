"""Regression tests for issue #5013.

Tests that next_id method handles negative and zero IDs correctly,
ensuring new todos always get positive integer IDs.

Bug: next_id method didn't filter out non-positive IDs, which could
result in producing ID=0 or negative IDs for new todos.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdHandlesNegativeAndZeroIds:
    """Tests for next_id with edge cases involving non-positive IDs."""

    def test_next_id_with_negative_id_returns_positive(self) -> None:
        """Test next_id returns 1 when todos contains only negative ID.

        Previously: next_id([Todo(id=-5,text='x')]) would return -4.
        Fixed: Should return 1 (start from 1 if no positive IDs exist).
        """
        storage = TodoStorage(":memory:")
        todos = [Todo(id=-5, text="negative id")]
        assert storage.next_id(todos) == 1

    def test_next_id_with_zero_id_returns_positive(self) -> None:
        """Test next_id returns 1 when todos contains only id=0.

        Previously: next_id([Todo(id=0,text='x')]) would return 1.
        This was actually correct, but should be explicit.
        """
        storage = TodoStorage(":memory:")
        todos = [Todo(id=0, text="zero id")]
        assert storage.next_id(todos) == 1

    def test_next_id_with_mixed_positive_and_negative_ids(self) -> None:
        """Test next_id returns max positive + 1 when mixed IDs exist.

        Previously: next_id([Todo(id=-1), Todo(id=3)]) would return 4.
        This was already correct because max of -1 and 3 is 3.
        """
        storage = TodoStorage(":memory:")
        todos = [Todo(id=-1, text="negative"), Todo(id=3, text="positive")]
        assert storage.next_id(todos) == 4

    def test_next_id_with_only_zero_and_negative_ids(self) -> None:
        """Test next_id returns 1 when all IDs are non-positive.

        This tests the edge case where we have multiple non-positive IDs.
        """
        storage = TodoStorage(":memory:")
        todos = [
            Todo(id=-5, text="negative 1"),
            Todo(id=-1, text="negative 2"),
            Todo(id=0, text="zero"),
        ]
        assert storage.next_id(todos) == 1

    def test_next_id_with_large_negative_ids(self) -> None:
        """Test next_id handles large negative IDs correctly."""
        storage = TodoStorage(":memory:")
        todos = [Todo(id=-999999, text="large negative")]
        assert storage.next_id(todos) == 1

    def test_next_id_with_positive_ids_ignores_negatives(self) -> None:
        """Test that negative IDs are ignored when positive IDs exist."""
        storage = TodoStorage(":memory:")
        todos = [
            Todo(id=-100, text="negative"),
            Todo(id=5, text="positive 1"),
            Todo(id=10, text="positive 2"),
        ]
        # Should return max positive (10) + 1 = 11, not -99 or 11
        assert storage.next_id(todos) == 11

    def test_next_id_empty_list_returns_1(self) -> None:
        """Test next_id returns 1 for empty todo list."""
        storage = TodoStorage(":memory:")
        assert storage.next_id([]) == 1

    def test_next_id_never_returns_non_positive(self) -> None:
        """Test that next_id never returns 0 or negative values."""
        storage = TodoStorage(":memory:")

        # Test various edge cases
        test_cases = [
            [Todo(id=-1, text="a")],
            [Todo(id=0, text="a")],
            [Todo(id=-100, text="a"), Todo(id=-50, text="b")],
            [Todo(id=-10, text="a"), Todo(id=0, text="b")],
        ]

        for todos in test_cases:
            result = storage.next_id(todos)
            assert result >= 1, f"next_id returned non-positive value {result} for {[t.id for t in todos]}"
