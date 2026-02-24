"""Regression test for issue #5492: next_id O(n) performance.

This test verifies that next_id completes in O(1) time regardless of list size,
by caching the max_id instead of scanning the entire list on each call.
"""

from __future__ import annotations

import time

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdPerformance:
    """Test suite for next_id performance optimization (issue #5492)."""

    def test_next_id_empty_list(self, tmp_path) -> None:
        """Test next_id returns 1 for empty list."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Empty list should return 1
        result = storage.next_id([])
        assert result == 1

    def test_next_id_single_item(self, tmp_path) -> None:
        """Test next_id returns max_id + 1 for single item."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=5, text="test")]
        result = storage.next_id(todos)
        assert result == 6

    def test_next_id_multiple_items(self, tmp_path) -> None:
        """Test next_id returns max_id + 1 for multiple items."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=3, text="c")]
        result = storage.next_id(todos)
        assert result == 6

    def test_next_id_gaps_preserved(self, tmp_path) -> None:
        """Test that next_id does not fill gaps from deleted items."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # IDs 1, 2, 5 exist (3, 4 were "deleted")
        todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=5, text="c")]
        result = storage.next_id(todos)
        # Should return 6, not 3 (not reusing gaps)
        assert result == 6

    def test_next_id_o1_performance(self, tmp_path) -> None:
        """Regression test for issue #5492: next_id should be O(1).

        Verifies that next_id completes in constant time regardless of list size.
        With O(n) implementation, 10000 items would take ~1000x longer than 10 items.
        With O(1) implementation, times should be approximately equal.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Test with small list (10 items) - use save() to populate cache
        small_todos = [Todo(id=i, text=f"task-{i}") for i in range(1, 11)]
        storage.save(small_todos)
        storage.load()  # Populate cache from load

        start_small = time.perf_counter()
        for _ in range(100):
            storage.next_id(small_todos)
        time_small = time.perf_counter() - start_small

        # Test with large list (10000 items)
        large_todos = [Todo(id=i, text=f"task-{i}") for i in range(1, 10001)]
        storage.save(large_todos)
        storage.load()  # Populate cache from load

        start_large = time.perf_counter()
        for _ in range(100):
            storage.next_id(large_todos)
        time_large = time.perf_counter() - start_large

        # With O(1) implementation, large list should not be significantly slower
        # Allow up to 10x ratio (not 1000x as with O(n))
        # This is a generous bound to account for variance
        ratio = time_large / time_small if time_small > 0 else 1.0

        # If implementation is O(n), ratio would be ~1000
        # If implementation is O(1), ratio should be close to 1
        # We use 50x as threshold to allow for variance but catch O(n)
        assert ratio < 50, (
            f"next_id appears to be O(n): 10000 items took {ratio:.1f}x longer than 10 items "
            f"(time_small={time_small:.6f}s, time_large={time_large:.6f}s). "
            f"Expected O(1) behavior with ratio < 50."
        )

    def test_next_id_after_load_updates_cache(self, tmp_path) -> None:
        """Test that loading todos updates the cached max_id."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save some todos
        todos = [Todo(id=10, text="a"), Todo(id=20, text="b")]
        storage.save(todos)

        # Load them back
        loaded = storage.load()

        # next_id should use cached max_id from load
        result = storage.next_id(loaded)
        assert result == 21

    def test_next_id_consistency_after_operations(self, tmp_path) -> None:
        """Test next_id returns consistent values across multiple calls."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=5, text="test")]

        # Multiple calls should return the same value (doesn't mutate state)
        result1 = storage.next_id(todos)
        result2 = storage.next_id(todos)
        result3 = storage.next_id(todos)

        assert result1 == result2 == result3 == 6
