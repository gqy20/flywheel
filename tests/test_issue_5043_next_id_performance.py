"""Tests for next_id() performance - Issue #5043.

next_id() should use O(1) complexity, not O(n) linear scan via max().

This test verifies that next_id() runs in constant time regardless of
the number of todos, by maintaining a cached max_id counter.
"""

from __future__ import annotations

import time

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdPerformance:
    """Performance tests for next_id() method."""

    def test_next_id_is_constant_time_for_large_datasets(self) -> None:
        """next_id() should have O(1) time complexity after cache warmup.

        Regression test for Issue #5043: next_id() uses O(n) linear scan
        via max() which is inefficient for large datasets.

        Verifies that once the cache is warmed (after first call or save()),
        subsequent next_id() calls are constant time regardless of list size.
        """
        storage = TodoStorage(":memory:")  # Doesn't matter, we're testing the method

        # Create a small list of todos
        small_list = [Todo(id=i, text=f"todo {i}") for i in range(10)]

        # Create a large list of todos (10000 items as per acceptance criteria)
        large_list = [Todo(id=i, text=f"todo {i}") for i in range(10000)]

        # Warm up the cache for small list with first call
        storage.next_id(small_list)

        # Measure time for small list (average of multiple calls - cache is warm)
        small_times = []
        for _ in range(100):
            start = time.perf_counter()
            storage.next_id(small_list)
            small_times.append(time.perf_counter() - start)
        small_avg = sum(small_times) / len(small_times)

        # Reset cache to test large list
        storage._max_id_cache = None

        # Warm up the cache for large list with first call
        storage.next_id(large_list)

        # Measure time for large list (average of multiple calls - cache is warm)
        large_times = []
        for _ in range(100):
            start = time.perf_counter()
            storage.next_id(large_list)
            large_times.append(time.perf_counter() - start)
        large_avg = sum(large_times) / len(large_times)

        # For O(1) implementation, the time difference should be minimal
        # For O(n) implementation with 1000x more items, it would be ~1000x slower
        # We allow a small factor to account for measurement noise
        ratio = large_avg / small_avg if small_avg > 0 else large_avg

        # If O(1), ratio should be close to 1 (with some tolerance for noise)
        # We set the threshold at 5 to allow for measurement noise
        assert ratio < 5, (
            f"next_id() appears to have O(n) complexity: "
            f"large list (10000 items) took {ratio:.1f}x longer than small list (10 items). "
            f"Expected O(1) behavior with ratio < 5, got {ratio:.1f}. "
            f"Small avg: {small_avg * 1000:.3f}ms, Large avg: {large_avg * 1000:.3f}ms"
        )

    def test_next_id_returns_correct_value_with_empty_list(self) -> None:
        """next_id() should return 1 for an empty list."""
        storage = TodoStorage(":memory:")
        assert storage.next_id([]) == 1

    def test_next_id_returns_correct_value_with_todos(self) -> None:
        """next_id() should return max_id + 1 for a list with todos."""
        storage = TodoStorage(":memory:")
        todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=3, text="c")]
        assert storage.next_id(todos) == 6

    def test_next_id_handles_large_dataset_under_10ms(self) -> None:
        """Benchmark: next_id with 10000 todos should complete in <10ms.

        This is the acceptance criterion from Issue #5043.
        """
        storage = TodoStorage(":memory:")
        large_list = [Todo(id=i, text=f"todo {i}") for i in range(10000)]

        # Run multiple times to get stable measurement
        times = []
        for _ in range(10):
            start = time.perf_counter()
            storage.next_id(large_list)
            times.append(time.perf_counter() - start)

        avg_time_ms = (sum(times) / len(times)) * 1000

        assert avg_time_ms < 10, (
            f"next_id() took {avg_time_ms:.2f}ms on average for 10000 todos, "
            f"expected < 10ms per acceptance criteria"
        )
