"""Regression test for issue #4020: next_id() has O(n) complexity.

This test verifies that next_id() completes in O(1) time regardless of
the number of todos, ensuring it doesn't scan all todos to find the max ID.
"""

from __future__ import annotations

import time
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdPerformance:
    """Test that next_id() operates in O(1) time."""

    def test_next_id_constant_time_with_large_todo_lists(self, tmp_path: Path) -> None:
        """Verify next_id() completes in constant time regardless of todo count.

        This is a performance regression test. If next_id() scans all todos
        using max(), execution time will grow linearly with todo count.
        With O(1) implementation, time should be constant.

        We measure time for 1000 vs 10000 todos and expect no more than 2x
        difference (allowing for some variance), whereas O(n) would show 10x.
        """
        db = tmp_path / "perf_test.json"
        storage = TodoStorage(str(db))

        # Measure time with 1000 todos
        todos_1k = [Todo(id=i, text=f"task {i}") for i in range(1, 1001)]
        storage.save(todos_1k)

        # Warm up and measure
        for _ in range(10):
            storage.next_id(todos_1k)

        start_1k = time.perf_counter()
        for _ in range(100):
            storage.next_id(todos_1k)
        time_1k = time.perf_counter() - start_1k

        # Measure time with 10000 todos
        todos_10k = [Todo(id=i, text=f"task {i}") for i in range(1, 10001)]
        storage.save(todos_10k)

        # Warm up
        for _ in range(10):
            storage.next_id(todos_10k)

        start_10k = time.perf_counter()
        for _ in range(100):
            storage.next_id(todos_10k)
        time_10k = time.perf_counter() - start_10k

        # Calculate ratio: O(n) would give ~10x, O(1) should give ~1x
        # Allow generous tolerance for CI variability (3x instead of 10x)
        ratio = time_10k / time_1k if time_1k > 0 else 0

        # If next_id() is O(n), ratio should be close to 10
        # If next_id() is O(1), ratio should be close to 1
        # We use a threshold of 3 to allow for variance while catching O(n)
        assert ratio < 3, (
            f"next_id() appears to have O(n) complexity. "
            f"Time ratio for 10x data was {ratio:.1f}x (expected <3x for O(1)). "
            f"Time with 1k todos: {time_1k*1000:.2f}ms, "
            f"Time with 10k todos: {time_10k*1000:.2f}ms"
        )

    def test_next_id_returns_correct_value_after_load(self, tmp_path: Path) -> None:
        """Verify next_id() returns max_id + 1 after loading from storage."""
        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        # Save todos with IDs 1, 5, 10
        todos = [
            Todo(id=1, text="first"),
            Todo(id=5, text="fifth"),
            Todo(id=10, text="tenth"),
        ]
        storage.save(todos)

        # Load and verify next_id returns 11
        loaded = storage.load()
        assert storage.next_id(loaded) == 11

    def test_next_id_with_empty_storage(self, tmp_path: Path) -> None:
        """Verify next_id() returns 1 for empty storage."""
        db = tmp_path / "empty.json"
        storage = TodoStorage(str(db))

        todos = storage.load()
        assert len(todos) == 0
        assert storage.next_id(todos) == 1

    def test_next_id_increments_after_add(self, tmp_path: Path) -> None:
        """Verify next_id increments correctly after adding todos."""
        db = tmp_path / "increment.json"
        storage = TodoStorage(str(db))

        # First add
        todos = storage.load()
        next_id = storage.next_id(todos)
        assert next_id == 1
        todos.append(Todo(id=next_id, text="first"))
        storage.save(todos)

        # Second add
        todos = storage.load()
        next_id = storage.next_id(todos)
        assert next_id == 2
        todos.append(Todo(id=next_id, text="second"))
        storage.save(todos)

        # Third add
        todos = storage.load()
        next_id = storage.next_id(todos)
        assert next_id == 3
