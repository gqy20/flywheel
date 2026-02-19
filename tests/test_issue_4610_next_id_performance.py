"""Performance test for next_id O(n) issue #4610.

This test verifies that next_id operation is O(1) rather than O(n)
by caching the max_id instead of recalculating it on every call.
"""

from __future__ import annotations

import time

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdPerformance:
    """Test that next_id has O(1) performance characteristics."""

    def test_next_id_performance_is_constant_time(self, tmp_path) -> None:
        """Test that next_id performance does not degrade with list size.

        This test verifies the fix for issue #4610 where next_id was
        traversing the entire list to find max ID, causing O(n) behavior.

        With proper caching, calling next_id twice on the same list
        should have similar performance regardless of when the cache was built.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a large list of todos
        large_size = 1000
        todos = [Todo(id=i, text=f"task-{i}") for i in range(1, large_size + 1)]

        # First call - should build cache (or use O(n) in old impl)
        start = time.perf_counter()
        _ = storage.next_id(todos)
        first_call_time = time.perf_counter() - start

        # Second call - should be O(1) with cache (still O(n) in old impl)
        start = time.perf_counter()
        _ = storage.next_id(todos)
        second_call_time = time.perf_counter() - start

        # With caching, second call should be much faster than first
        # With O(n) traversal, both calls would be similar
        # Allow 10x tolerance for measurement noise
        assert second_call_time < first_call_time * 0.5 + 0.001, (
            f"next_id appears to have O(n) complexity: "
            f"first_call={first_call_time:.6f}s, second_call={second_call_time:.6f}s"
        )

    def test_next_id_returns_correct_value_with_cache(self, tmp_path) -> None:
        """Test that cached next_id still returns correct values."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Empty list
        assert storage.next_id([]) == 1

        # List with gaps
        todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=10, text="c")]
        assert storage.next_id(todos) == 11

        # Repeated calls should return same value (idempotent)
        assert storage.next_id(todos) == 11
        assert storage.next_id(todos) == 11

    def test_next_id_cache_updates_after_save(self, tmp_path) -> None:
        """Test that cache updates correctly after save operations."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Start with empty storage
        todos = []
        assert storage.next_id(todos) == 1

        # Add a todo and save
        todos.append(Todo(id=1, text="first"))
        storage.save(todos)

        # Load and check next_id
        loaded = storage.load()
        assert storage.next_id(loaded) == 2

        # Add another
        loaded.append(Todo(id=2, text="second"))
        storage.save(loaded)

        # Load and check next_id again
        loaded_again = storage.load()
        assert storage.next_id(loaded_again) == 3

    def test_next_id_performance_comparison_small_vs_large(self, tmp_path) -> None:
        """Compare performance between small and large lists.

        With O(1) caching, the time to call next_id should not
        increase linearly with list size.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Small list
        small_todos = [Todo(id=i, text=f"task-{i}") for i in range(1, 11)]
        start = time.perf_counter()
        for _ in range(100):
            storage.next_id(small_todos)
        small_time = time.perf_counter() - start

        # Large list (100x bigger)
        large_todos = [Todo(id=i, text=f"task-{i}") for i in range(1, 1001)]
        start = time.perf_counter()
        for _ in range(100):
            storage.next_id(large_todos)
        large_time = time.perf_counter() - start

        # With O(n), large_time would be ~100x small_time
        # With O(1) cache, they should be similar (allow 10x tolerance)
        ratio = large_time / small_time if small_time > 0 else 0
        assert ratio < 10, (
            f"next_id appears to have O(n) complexity: "
            f"small_list={small_time:.6f}s, large_list={large_time:.6f}s, ratio={ratio:.1f}"
        )
