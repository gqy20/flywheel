"""Tests for issue #6855: next_id() O(n) complexity performance fix.

This test suite verifies that next_id() has O(1) complexity instead of O(n)
by caching the max_id in the TodoStorage instance.

Performance regression test: Adding todos should remain fast even with large lists.
"""

from __future__ import annotations

import time
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdPerformance:
    """Test suite for next_id() performance optimization."""

    def test_next_id_is_o1_not_on(self, tmp_path: Path) -> None:
        """Verify next_id() has O(1) complexity, not O(n).

        This test verifies that calling next_id() multiple times on a large list
        doesn't have linear time complexity. With O(n) implementation, calling
        next_id() 100 times on a 1000-item list would take ~100x longer than
        calling it once. With O(1) caching, it should be nearly constant.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a large list of todos
        large_todo_count = 1000
        todos = [Todo(id=i, text=f"task {i}") for i in range(1, large_todo_count + 1)]

        # Measure time for multiple next_id() calls
        iterations = 100

        start = time.perf_counter()
        for _ in range(iterations):
            storage.next_id(todos)
        elapsed = time.perf_counter() - start

        # With O(n) implementation, 100 calls on 1000 items = ~100000 operations
        # With O(1) implementation, 100 calls = ~100 operations
        # We expect the cached version to complete in well under 0.1 seconds
        # The O(n) version would typically take 0.1-0.5 seconds for this many calls
        assert elapsed < 0.1, (
            f"next_id() appears to have O(n) complexity: "
            f"{iterations} calls took {elapsed:.3f}s on {large_todo_count} items. "
            f"Expected O(1) implementation to complete in < 0.1s."
        )

    def test_next_id_returns_correct_value_after_add(self, tmp_path: Path) -> None:
        """Verify next_id() returns correct sequential IDs after adding todos."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]

        # next_id should return max_id + 1
        assert storage.next_id(todos) == 3

        # Add a todo with higher ID
        todos.append(Todo(id=10, text="tenth"))
        assert storage.next_id(todos) == 11

    def test_next_id_handles_empty_list(self, tmp_path: Path) -> None:
        """Verify next_id() returns 1 for empty list."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        assert storage.next_id([]) == 1

    def test_next_id_handles_single_item(self, tmp_path: Path) -> None:
        """Verify next_id() works correctly with single item."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=5, text="fifth")]
        assert storage.next_id(todos) == 6

    def test_next_id_handles_sparse_ids(self, tmp_path: Path) -> None:
        """Verify next_id() returns max_id + 1 even with gaps in IDs."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # IDs with gaps: 1, 5, 10, 100
        todos = [
            Todo(id=1, text="first"),
            Todo(id=5, text="fifth"),
            Todo(id=10, text="tenth"),
            Todo(id=100, text="hundredth"),
        ]
        assert storage.next_id(todos) == 101

    def test_next_id_performance_scales_linearly_with_calls(self, tmp_path: Path) -> None:
        """Verify next_id() time scales with number of calls, not list size.

        This is a more robust performance test: calling next_id() N times on a
        list of size M should take approximately the same time regardless of M
        if the implementation is O(1) after the initial cache population.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Test with different list sizes
        sizes = [100, 500, 1000]
        iterations = 50
        times = []

        for size in sizes:
            todos = [Todo(id=i, text=f"task {i}") for i in range(1, size + 1)]

            # Warm up: first call populates cache
            storage.next_id(todos)

            start = time.perf_counter()
            for _ in range(iterations):
                storage.next_id(todos)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        # With O(1) implementation, time should not grow proportionally to list size
        # after cache population. time_1000 should be similar to time_100.
        # We allow up to 3x tolerance for system variance.
        # With O(n) implementation, time_1000 would be ~10x time_100
        ratio = times[2] / times[0] if times[0] > 0 else 0
        assert ratio < 3, (
            f"next_id() appears to scale with list size (O(n)): "
            f"time for 1000 items is {ratio:.1f}x time for 100 items. "
            f"Expected O(1) implementation to have ratio < 3. "
            f"Times: 100={times[0]:.4f}s, 500={times[1]:.4f}s, 1000={times[2]:.4f}s"
        )
