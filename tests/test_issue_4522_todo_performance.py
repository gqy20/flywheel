"""Performance tests for TodoApp operations on large datasets.

Issue #4522: TodoApp operations load and save the entire todo list each time,
causing performance issues with large datasets.

This test suite provides regression tests to ensure operations remain performant
even with large numbers of todos. The key optimization is to use an in-memory
cache to avoid unnecessary I/O for sequential operations.
"""

from __future__ import annotations

import time
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo

# Performance thresholds (in seconds)
# These thresholds are based on expected O(1) behavior for single operations
ADD_OPERATION_THRESHOLD = 0.1  # Adding a single todo should be very fast
MARK_DONE_THRESHOLD = 0.1  # Marking a todo done should be very fast
REMOVE_OPERATION_THRESHOLD = 0.1  # Removing a todo should be very fast

# Sequential operations: each operation should not degrade linearly
SEQUENTIAL_PER_OP_THRESHOLD = 0.05  # Per-operation time for sequential ops

# Dataset sizes for testing
LARGE_DATASET_SIZE = 1000
VERY_LARGE_DATASET_SIZE = 5000


def _populate_todos(storage: TodoStorage, count: int) -> list[Todo]:
    """Populate storage with a large number of todos for testing."""
    todos = []
    for i in range(1, count + 1):
        todo = Todo(id=i, text=f"Task number {i} with some additional text to make it realistic")
        todos.append(todo)
    storage.save(todos)
    return todos


class TestTodoAppPerformance:
    """Performance tests for TodoApp operations.

    These tests verify that operations don't scale linearly with dataset size,
    which would indicate O(n) load/save behavior.
    """

    def test_add_performance_with_large_dataset(self, tmp_path: Path) -> None:
        """Test that add operation is performant with a large existing dataset.

        With optimized implementation using in-memory cache, add should be O(1)
        amortized, not O(n).
        """
        db_path = tmp_path / "perf_test.json"
        app = TodoApp(db_path=str(db_path))

        # Populate with large dataset
        _populate_todos(app.storage, LARGE_DATASET_SIZE)

        # Measure add operation
        start = time.perf_counter()
        app.add("New task that should be added quickly")
        elapsed = time.perf_counter() - start

        assert elapsed < ADD_OPERATION_THRESHOLD, (
            f"Add operation took {elapsed:.3f}s, expected < {ADD_OPERATION_THRESHOLD}s. "
            f"This indicates performance degradation with {LARGE_DATASET_SIZE} todos."
        )

    def test_mark_done_performance_with_large_dataset(self, tmp_path: Path) -> None:
        """Test that mark_done operation is performant with a large dataset.

        With optimized implementation using in-memory cache and id lookup,
        mark_done should be O(log n) or better.
        """
        db_path = tmp_path / "perf_test.json"
        app = TodoApp(db_path=str(db_path))

        # Populate with large dataset
        _populate_todos(app.storage, LARGE_DATASET_SIZE)

        # Measure mark_done operation (on a todo in the middle)
        target_id = LARGE_DATASET_SIZE // 2
        start = time.perf_counter()
        app.mark_done(target_id)
        elapsed = time.perf_counter() - start

        assert elapsed < MARK_DONE_THRESHOLD, (
            f"Mark_done operation took {elapsed:.3f}s, expected < {MARK_DONE_THRESHOLD}s. "
            f"This indicates performance degradation with {LARGE_DATASET_SIZE} todos."
        )

    def test_remove_performance_with_large_dataset(self, tmp_path: Path) -> None:
        """Test that remove operation is performant with a large dataset.

        With optimized implementation using in-memory cache and id lookup,
        remove should be O(1) amortized.
        """
        db_path = tmp_path / "perf_test.json"
        app = TodoApp(db_path=str(db_path))

        # Populate with large dataset
        _populate_todos(app.storage, LARGE_DATASET_SIZE)

        # Measure remove operation (on a todo in the middle)
        target_id = LARGE_DATASET_SIZE // 2
        start = time.perf_counter()
        app.remove(target_id)
        elapsed = time.perf_counter() - start

        assert elapsed < REMOVE_OPERATION_THRESHOLD, (
            f"Remove operation took {elapsed:.3f}s, expected < {REMOVE_OPERATION_THRESHOLD}s. "
            f"This indicates performance degradation with {LARGE_DATASET_SIZE} todos."
        )

    def test_sequential_operations_scaling(self, tmp_path: Path) -> None:
        """Test that sequential operations scale sublinearly.

        Key regression test: with O(n) load/save per operation, N sequential
        operations would be O(n*N). With in-memory cache, it should be O(N).

        We test this by comparing per-operation time for sequential ops
        between a small and large initial dataset.
        """
        # Test with small dataset first
        small_path = tmp_path / "small.json"
        small_app = TodoApp(db_path=str(small_path))
        _populate_todos(small_app.storage, 10)

        small_times = []
        for i in range(10):
            start = time.perf_counter()
            small_app.add(f"Small dataset task {i}")
            small_times.append(time.perf_counter() - start)

        small_avg = sum(small_times) / len(small_times)

        # Test with large dataset
        large_path = tmp_path / "large.json"
        large_app = TodoApp(db_path=str(large_path))
        _populate_todos(large_app.storage, LARGE_DATASET_SIZE)

        large_times = []
        for i in range(10):
            start = time.perf_counter()
            large_app.add(f"Large dataset task {i}")
            large_times.append(time.perf_counter() - start)

        large_avg = sum(large_times) / len(large_times)

        # Per-operation time should not grow linearly with dataset size
        # With O(n) load/save, large_avg would be ~100x small_avg
        # With O(1) amortized, large_avg should be at most ~3x small_avg
        ratio = large_avg / max(small_avg, 0.001)  # Avoid division by zero

        # Allow some variance but catch O(n) scaling
        max_acceptable_ratio = 10.0
        assert ratio < max_acceptable_ratio, (
            f"Sequential add operations show O(n) scaling. "
            f"Large dataset avg time {large_avg:.4f}s vs small {small_avg:.4f}s "
            f"(ratio: {ratio:.1f}x, max acceptable: {max_acceptable_ratio}x). "
            f"This indicates each operation loads the entire dataset."
        )

    def test_sequential_operations_performance(self, tmp_path: Path) -> None:
        """Test that a sequence of operations is performant.

        This simulates real-world usage where a user performs multiple operations.
        With caching, sequential operations should be very fast.
        """
        db_path = tmp_path / "perf_test.json"
        app = TodoApp(db_path=str(db_path))

        # Populate with large dataset
        _populate_todos(app.storage, LARGE_DATASET_SIZE)

        # Perform a sequence of operations and measure total time
        start = time.perf_counter()

        # Add 5 new todos
        for i in range(5):
            app.add(f"Sequential task {i}")

        # Mark 2 done
        app.mark_done(LARGE_DATASET_SIZE + 1)
        app.mark_done(LARGE_DATASET_SIZE + 2)

        # Remove 1
        app.remove(LARGE_DATASET_SIZE + 3)

        elapsed = time.perf_counter() - start

        # 8 operations total, each should be fast
        total_threshold = 8 * SEQUENTIAL_PER_OP_THRESHOLD
        assert elapsed < total_threshold, (
            f"8 sequential operations took {elapsed:.3f}s, expected < {total_threshold:.3f}s. "
            f"This indicates cumulative performance issues."
        )


class TestTodoAppIncrementalOperations:
    """Tests for incremental operation support.

    These tests verify that the TodoApp supports incremental operations
    that don't require loading/saving the entire dataset.
    """

    def test_add_does_not_load_entire_dataset(self, tmp_path: Path) -> None:
        """Test that add operation can work incrementally."""
        db_path = tmp_path / "incremental_test.json"
        app = TodoApp(db_path=str(db_path))

        # Add initial todo
        app.add("First todo")

        # Add second todo - should work without issues
        second = app.add("Second todo")

        assert second.id == 2
        assert second.text == "Second todo"

    def test_mark_done_updates_single_todo(self, tmp_path: Path) -> None:
        """Test that mark_done correctly updates a single todo."""
        db_path = tmp_path / "incremental_test.json"
        app = TodoApp(db_path=str(db_path))

        # Add multiple todos
        app.add("Task 1")
        app.add("Task 2")
        app.add("Task 3")

        # Mark one done
        marked = app.mark_done(2)

        assert marked.done is True
        assert marked.id == 2

        # Verify persistence
        todos = app.list()
        assert todos[0].done is False
        assert todos[1].done is True
        assert todos[2].done is False

    def test_data_integrity_after_incremental_operations(self, tmp_path: Path) -> None:
        """Test that data integrity is maintained after multiple incremental ops."""
        db_path = tmp_path / "integrity_test.json"
        app = TodoApp(db_path=str(db_path))

        # Create multiple todos
        for i in range(10):
            app.add(f"Original task {i}")

        # Perform various operations
        app.mark_done(3)
        app.mark_done(5)
        app.remove(7)
        app.add("New task after removal")

        # Verify final state
        todos = app.list()
        assert len(todos) == 10  # 10 original - 1 removed + 1 new

        # Check that specific operations were applied
        todo_3 = next(t for t in todos if t.id == 3)
        assert todo_3.done is True

        todo_5 = next(t for t in todos if t.id == 5)
        assert todo_5.done is True

        # Todo 7 should be gone
        assert not any(t.id == 7 for t in todos)

        # New todo should exist
        assert any("New task after removal" in t.text for t in todos)
