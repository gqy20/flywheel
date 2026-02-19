"""Regression test for issue #4561: O(n) ID generation scans entire list on every add().

This test verifies that next_id() is O(1) regardless of list size, not O(n).
The original implementation used max() which scans all items on every call.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestO1NextId:
    """Tests for O(1) next_id performance."""

    def test_next_id_is_o1_time_complexity(self, tmp_path: Path) -> None:
        """Verify next_id() has O(1) time complexity, not O(n).

        This test fails with the original O(n) max() implementation
        and passes with the O(1) cached max_id implementation.
        """
        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        # Measure time for next_id with 100 items
        todos_100 = [Todo(id=i, text=f"task {i}") for i in range(1, 101)]
        start_100 = time.perf_counter()
        for _ in range(100):
            storage.next_id(todos_100)
        time_100 = time.perf_counter() - start_100

        # Measure time for next_id with 10000 items (100x more)
        todos_10000 = [Todo(id=i, text=f"task {i}") for i in range(1, 10001)]
        start_10000 = time.perf_counter()
        for _ in range(100):
            storage.next_id(todos_10000)
        time_10000 = time.perf_counter() - start_10000

        # For O(1) implementation, time should NOT grow linearly
        # Allow some variance, but 100x more items should NOT take 100x longer
        # With O(n) it would be ~100x slower; with O(1) it should be roughly same
        # We use a generous threshold: 100x more items should not be more than 5x slower
        ratio = time_10000 / time_100 if time_100 > 0 else 1.0
        assert ratio < 5.0, (
            f"next_id appears to be O(n): "
            f"100 items took {time_100:.4f}s, "
            f"10000 items took {time_10000:.4f}s "
            f"(ratio: {ratio:.1f}x, expected < 5x for O(1))"
        )

    def test_next_id_returns_correct_value_with_cached_max(self, tmp_path: Path) -> None:
        """Verify next_id returns correct value on first call."""
        # Each storage instance should correctly compute max_id on first call
        storage = TodoStorage(str(tmp_path / "test.json"))

        # Test empty list
        assert storage.next_id([]) == 1

        # Test list with single item - use fresh storage instance
        storage2 = TodoStorage(str(tmp_path / "test2.json"))
        todos = [Todo(id=5, text="test")]
        assert storage2.next_id(todos) == 6

        # Test list with non-contiguous IDs - use fresh storage instance
        storage3 = TodoStorage(str(tmp_path / "test3.json"))
        todos = [Todo(id=1, text="a"), Todo(id=100, text="b"), Todo(id=50, text="c")]
        assert storage3.next_id(todos) == 101

        # Test list with max at start - use fresh storage instance
        storage4 = TodoStorage(str(tmp_path / "test4.json"))
        todos = [Todo(id=99, text="max first"), Todo(id=1, text="min")]
        assert storage4.next_id(todos) == 100

    def test_next_id_after_delete_handles_gaps(self, tmp_path: Path) -> None:
        """Verify next_id handles gaps correctly after deletions."""
        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        # Create todos and save them
        todos = [Todo(id=i, text=f"task {i}") for i in range(1, 11)]
        storage.save(todos)

        # Load and get next_id - should be 11
        loaded = storage.load()
        assert storage.next_id(loaded) == 11

        # Simulate deletion: save a list with a gap, reload, get next_id
        todos_with_gap = [Todo(id=i, text=f"task {i}") for i in range(1, 11) if i != 5]
        storage.save(todos_with_gap)

        # Fresh storage instance to simulate new add() call
        storage2 = TodoStorage(str(db))
        reloaded = storage2.load()
        # After deleting task 5, max is still 10, so next_id should be 11
        assert storage2.next_id(reloaded) == 11

    def test_next_id_with_large_max_id(self, tmp_path: Path) -> None:
        """Verify next_id handles very large ID values."""
        storage = TodoStorage(str(tmp_path / "test.json"))

        # Test with a very large max ID
        todos = [Todo(id=999999, text="large id")]
        assert storage.next_id(todos) == 1000000

    def test_next_id_consecutive_calls_increasing(self, tmp_path: Path) -> None:
        """Verify consecutive calls to next_id with cached storage return increasing values."""
        db_path = tmp_path / "test.json"
        storage = TodoStorage(str(db_path))

        todos: list[Todo] = []

        # First call should return 1
        id1 = storage.next_id(todos)
        assert id1 == 1

        # Simulate real usage: save with new id, then subsequent calls use cache
        todos.append(Todo(id=id1, text="first"))
        storage.save(todos)

        # Subsequent calls should return incrementing values from cache (O(1))
        id2 = storage.next_id(todos)
        assert id2 == 2
        id3 = storage.next_id(todos)
        assert id3 == 3

        # After many calls, cache should continue incrementing
        for expected in range(4, 104):
            assert storage.next_id(todos) == expected
