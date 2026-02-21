"""Regression test for issue #5043: next_id() O(n) performance.

This test ensures that next_id() performs efficiently even with large datasets.
The original implementation used O(n) linear scan via max() which was inefficient
for large todo lists.

The fix maintains a cached max_id to achieve O(1) performance.
"""

from __future__ import annotations

import time

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdPerformance:
    """Tests for next_id() performance characteristics."""

    def test_next_id_performance_with_large_dataset(self, tmp_path) -> None:
        """Test that next_id() performs in O(1) time, not O(n).

        This test creates a large dataset and measures the time to compute
        the next ID. The implementation should be O(1) regardless of dataset size.
        """
        db = tmp_path / "perf.json"
        storage = TodoStorage(str(db))

        # Create a large dataset
        large_count = 10000
        todos = [Todo(id=i, text=f"task-{i}") for i in range(1, large_count + 1)]

        # Measure time for next_id on large dataset
        start = time.perf_counter()
        next_id = storage.next_id(todos)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert next_id == large_count + 1
        # Acceptance criteria: should complete in < 10ms for 10000 todos
        assert elapsed_ms < 10, (
            f"next_id() took {elapsed_ms:.2f}ms for {large_count} todos, "
            f"expected < 10ms (O(1) implementation required)"
        )

    def test_next_id_performance_scales_constantly(self, tmp_path) -> None:
        """Test that next_id() scales constantly (O(1)), not linearly (O(n)).

        If next_id() is O(n), doubling the dataset size should roughly double
        the execution time. If it's O(1), the time should remain roughly constant.
        """
        db = tmp_path / "scale.json"
        storage = TodoStorage(str(db))

        # Measure with smaller dataset
        small_count = 5000
        small_todos = [Todo(id=i, text=f"task-{i}") for i in range(1, small_count + 1)]

        # Take average of multiple runs for more reliable timing
        small_times = []
        for _ in range(5):
            start = time.perf_counter()
            storage.next_id(small_todos)
            small_times.append((time.perf_counter() - start) * 1000)
        small_avg = sum(small_times) / len(small_times)

        # Measure with larger dataset (2x size)
        large_count = 10000
        large_todos = [Todo(id=i, text=f"task-{i}") for i in range(1, large_count + 1)]

        large_times = []
        for _ in range(5):
            start = time.perf_counter()
            storage.next_id(large_todos)
            large_times.append((time.perf_counter() - start) * 1000)
        large_avg = sum(large_times) / len(large_times)

        # For O(1) implementation, large_avg should be close to small_avg
        # For O(n) implementation, large_avg would be ~2x small_avg
        # We allow some variance but fail if large is significantly larger
        # A 50% increase threshold allows for noise while catching O(n) behavior
        ratio = large_avg / small_avg if small_avg > 0 else 1.0
        assert ratio < 1.5, (
            f"next_id() appears to have O(n) complexity. "
            f"Time ratio for 2x data was {ratio:.2f}x (expected ~1x for O(1)). "
            f"Small avg: {small_avg:.3f}ms, Large avg: {large_avg:.3f}ms"
        )

    def test_next_id_correctness_with_gaps(self, tmp_path) -> None:
        """Test that next_id() handles IDs with gaps correctly.

        When todos are deleted, there may be gaps in IDs. The next_id() should
        return max(existing_ids) + 1, not fill in gaps.
        """
        storage = TodoStorage(str(tmp_path / "gaps.json"))

        # Create todos with gaps (IDs 1, 3, 5, 7, 9)
        todos = [Todo(id=i, text=f"task-{i}") for i in [1, 3, 5, 7, 9]]

        next_id = storage.next_id(todos)
        assert next_id == 10, f"Expected next_id=10 (max+1), got {next_id}"

    def test_next_id_with_empty_list(self, tmp_path) -> None:
        """Test that next_id() returns 1 for empty list."""
        storage = TodoStorage(str(tmp_path / "empty.json"))
        next_id = storage.next_id([])
        assert next_id == 1

    def test_next_id_with_single_item(self, tmp_path) -> None:
        """Test that next_id() returns 2 for list with single item at id=1."""
        storage = TodoStorage(str(tmp_path / "single.json"))
        todos = [Todo(id=1, text="only task")]
        next_id = storage.next_id(todos)
        assert next_id == 2

    def test_next_id_with_high_ids(self, tmp_path) -> None:
        """Test that next_id() handles very high ID values correctly."""
        storage = TodoStorage(str(tmp_path / "high.json"))

        # Create todos with high IDs
        high_id = 1000000
        todos = [Todo(id=high_id, text="high id task")]

        next_id = storage.next_id(todos)
        assert next_id == high_id + 1
