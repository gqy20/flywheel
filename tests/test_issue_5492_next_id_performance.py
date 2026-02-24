"""Regression test for issue #5492: next_id uses O(n) max() scan on every add operation.

This test suite verifies that next_id completes in O(1) time regardless of list size,
addressing the performance issue where max() was iterating over the entire todos list.
"""

from __future__ import annotations

import time

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdPerformance:
    """Performance tests for next_id O(1) requirement."""

    def test_next_id_should_be_constant_time_regardless_of_list_size(self, tmp_path) -> None:
        """next_id should complete in O(1) time regardless of list size.

        This is a regression test for issue #5492 where next_id used O(n) max()
        scan on every add operation.

        The test measures next_id calls after load() has populated the cache.
        With O(1) caching, both small and large lists should take similar time.
        """
        # Prepare data - small list (10 items)
        small_todos = [Todo(id=i, text=f"task {i}") for i in range(1, 11)]
        storage_small = TodoStorage(str(tmp_path / "small.json"))
        storage_small.save(small_todos)
        loaded_small = storage_small.load()  # This populates cache

        # Measure next_id calls for small list (after cache is populated)
        start_small = time.perf_counter()
        for _ in range(1000):
            storage_small.next_id(loaded_small)
        time_small = time.perf_counter() - start_small

        # Prepare data - large list (10000 items)
        large_todos = [Todo(id=i, text=f"task {i}") for i in range(1, 10001)]
        storage_large = TodoStorage(str(tmp_path / "large.json"))
        storage_large.save(large_todos)
        loaded_large = storage_large.load()  # This populates cache

        # Measure next_id calls for large list (after cache is populated)
        start_large = time.perf_counter()
        for _ in range(1000):
            storage_large.next_id(loaded_large)
        time_large = time.perf_counter() - start_large

        # For O(1) implementation, the ratio should be close to 1.0
        # For O(n) implementation, the ratio would be ~1000x (10000/10)
        # We allow some overhead, but it should be well under 10x
        ratio = time_large / time_small if time_small > 0 else 0

        # If implementation is O(1), ratio should be near 1.0
        # If implementation is O(n), ratio would be ~1000
        # We use a threshold of 5x to account for any overhead
        assert ratio < 5.0, (
            f"next_id appears to be O(n) instead of O(1). "
            f"Time ratio for 10x data size: {ratio:.1f}x "
            f"(small: {time_small:.6f}s, large: {time_large:.6f}s). "
            f"Expected O(1) should have ratio close to 1.0."
        )

    def test_next_id_returns_correct_value_after_multiple_adds(self, tmp_path) -> None:
        """next_id should return correct incrementing values after multiple adds."""
        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        # Simulate the add operation flow
        todos: list[Todo] = []

        for i in range(1, 101):
            next_id = storage.next_id(todos)
            assert next_id == i, f"Expected next_id={i}, got {next_id}"
            todos.append(Todo(id=next_id, text=f"task {i}"))

    def test_next_id_handles_non_contiguous_ids(self) -> None:
        """next_id should handle cases where IDs are not contiguous (e.g., after removal)."""
        storage = TodoStorage(":memory:")

        # Create todos with non-contiguous IDs (simulating after removal)
        todos = [
            Todo(id=1, text="task 1"),
            Todo(id=5, text="task 5"),
            Todo(id=10, text="task 10"),
        ]

        # next_id should return max_id + 1, not fill in gaps
        next_id = storage.next_id(todos)
        assert next_id == 11, f"Expected next_id=11 (max+1), got {next_id}"

    def test_next_id_returns_1_for_empty_list(self) -> None:
        """next_id should return 1 for an empty list."""
        storage = TodoStorage(":memory:")
        todos: list[Todo] = []

        next_id = storage.next_id(todos)
        assert next_id == 1, f"Expected next_id=1 for empty list, got {next_id}"


# Additional benchmark that can be run independently
def benchmark_next_id_scaling() -> None:
    """Benchmark helper to measure next_id scaling with list size.

    Run with: uv run pytest tests/test_issue_5492_next_id_performance.py::benchmark_next_id_scaling -v -s
    """
    storage = TodoStorage(":memory:")
    sizes = [10, 100, 1000, 5000, 10000]

    print("\nnext_id performance scaling:")
    print("-" * 40)

    for size in sizes:
        todos = [Todo(id=i, text=f"task {i}") for i in range(1, size + 1)]

        # Warm up
        for _ in range(10):
            storage.next_id(todos)

        # Measure
        start = time.perf_counter()
        for _ in range(1000):
            storage.next_id(todos)
        elapsed = time.perf_counter() - start

        per_call = elapsed / 1000 * 1_000_000  # microseconds
        print(f"  {size:5d} items: {per_call:7.2f} μs/call")

    print("-" * 40)
    print("O(1) implementation: times should stay roughly constant")
    print("O(n) implementation: times should grow linearly with size")


if __name__ == "__main__":
    benchmark_next_id_scaling()
