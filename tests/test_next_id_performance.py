"""Performance regression tests for next_id() O(1) complexity.

Issue #4020: next_id() should have O(1) complexity, not O(n).
"""

from __future__ import annotations

import time

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdPerformance:
    """Tests to verify next_id() maintains O(1) complexity."""

    def test_next_id_constant_time_small_dataset(self, tmp_path) -> None:
        """next_id() should be fast with 10 todos."""
        db = tmp_path / "db.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=i + 1, text=f"todo {i}") for i in range(10)]
        storage.save(todos)
        loaded = storage.load()  # Load to populate cache

        start = time.perf_counter()
        result = storage.next_id(loaded)
        elapsed = time.perf_counter() - start

        assert result == 11
        assert elapsed < 0.001, f"next_id() took {elapsed}s for 10 todos"

    def test_next_id_constant_time_medium_dataset(self, tmp_path) -> None:
        """next_id() should be equally fast with 1000 todos (O(1) requirement)."""
        db = tmp_path / "db.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=i + 1, text=f"todo {i}") for i in range(1000)]
        storage.save(todos)
        loaded = storage.load()  # Load to populate cache

        start = time.perf_counter()
        result = storage.next_id(loaded)
        elapsed = time.perf_counter() - start

        assert result == 1001
        # O(1) should be < 1ms regardless of dataset size
        assert elapsed < 0.001, f"next_id() took {elapsed}s for 1000 todos (expected O(1))"

    def test_next_id_constant_time_large_dataset(self, tmp_path) -> None:
        """next_id() should be equally fast with 10000 todos (O(1) requirement).

        This test FAILS with O(n) implementation because max() iterates all todos.
        With O(1) caching, this should complete in < 1ms.
        """
        db = tmp_path / "db.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=i + 1, text=f"todo {i}") for i in range(10000)]
        storage.save(todos)

        # Load to populate the cache (this is the normal usage pattern)
        loaded = storage.load()

        start = time.perf_counter()
        result = storage.next_id(loaded)
        elapsed = time.perf_counter() - start

        assert result == 10001
        # O(1) should be < 1ms regardless of dataset size
        # O(n) will likely take > 1ms with 10000 items
        assert elapsed < 0.001, (
            f"next_id() took {elapsed}s for 10000 todos - likely O(n) complexity. "
            f"Expected O(1) with cached max_id."
        )

    def test_next_id_scales_constant_not_linear(self, tmp_path) -> None:
        """Verify next_id() execution time does not grow linearly with dataset size.

        With O(1) caching, 10x more items should take the same time.
        With O(n) scanning, 10x more items should take ~10x longer.
        """
        db = tmp_path / "db.json"
        storage = TodoStorage(str(db))

        # Measure with 100 items
        todos_100 = [Todo(id=i + 1, text=f"todo {i}") for i in range(100)]
        storage.save(todos_100)
        loaded_100 = storage.load()  # Load to populate cache

        times_100 = []
        for _ in range(10):
            start = time.perf_counter()
            storage.next_id(loaded_100)
            times_100.append(time.perf_counter() - start)
        avg_100 = sum(times_100) / len(times_100)

        # Measure with 1000 items (10x more)
        todos_1000 = [Todo(id=i + 1, text=f"todo {i}") for i in range(1000)]
        storage.save(todos_1000)
        loaded_1000 = storage.load()  # Load to populate cache

        times_1000 = []
        for _ in range(10):
            start = time.perf_counter()
            storage.next_id(loaded_1000)
            times_1000.append(time.perf_counter() - start)
        avg_1000 = sum(times_1000) / len(times_1000)

        # With O(1), the ratio should be ~1.0 (constant time)
        # With O(n), the ratio would be ~10.0 (linear growth)
        # Allow some variance but should definitely be < 5
        ratio = avg_1000 / max(avg_100, 1e-9)

        assert ratio < 5.0, (
            f"next_id() appears to have O(n) complexity: "
            f"100 items avg={avg_100*1000:.3f}ms, 1000 items avg={avg_1000*1000:.3f}ms, "
            f"ratio={ratio:.1f}x (expected ~1x for O(1), got ~{ratio:.1f}x)"
        )

    def test_next_id_without_todos(self, tmp_path) -> None:
        """next_id() should return 1 for empty storage."""
        db = tmp_path / "db.json"
        storage = TodoStorage(str(db))

        result = storage.next_id([])
        assert result == 1

    def test_next_id_after_loading_from_storage(self, tmp_path) -> None:
        """next_id() should work correctly after loading todos from storage.

        The cached max_id should be initialized correctly when todos exist.
        """
        db = tmp_path / "db.json"
        storage = TodoStorage(str(db))

        # Save some todos
        todos = [Todo(id=i + 1, text=f"todo {i}") for i in range(100)]
        storage.save(todos)

        # Create a new storage instance to test initialization
        storage2 = TodoStorage(str(db))
        loaded = storage2.load()

        # next_id should still work correctly
        result = storage2.next_id(loaded)
        assert result == 101

    def test_next_id_after_deleting_highest(self, tmp_path) -> None:
        """next_id() should handle gap IDs when highest is deleted.

        When todo with highest ID is deleted, next_id should still return
        a unique ID (max+1 pattern, not fill gaps).
        """
        db = tmp_path / "db.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=i + 1, text=f"todo {i}") for i in range(5)]
        storage.save(todos)

        # Delete the highest ID (5)
        todos = [t for t in todos if t.id != 5]
        storage.save(todos)

        # next_id should return 6 (max was 4, so 4+1=5... wait, max is now 4)
        # Actually, IDs are 1,2,3,4 so max is 4, next should be 5
        result = storage.next_id(todos)
        assert result == 5, f"Expected 5 (max existing + 1), got {result}"
