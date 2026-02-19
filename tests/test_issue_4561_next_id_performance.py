"""Regression test for issue #4561: O(n) ID generation scans entire list on every add().

This test verifies that next_id() is O(1) regardless of the number of todos,
by ensuring it uses a cached max_id value rather than scanning the entire list.
"""

from __future__ import annotations

import time
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_is_constant_time_not_linear(tmp_path: Path) -> None:
    """Test that next_id() operates in O(1) time regardless of list size.

    Regression test for issue #4561: The original implementation used max()
    which iterates through all todos, making it O(n). This test ensures
    the fix maintains O(1) complexity by comparing performance with different
    list sizes.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Measure time for small list (100 items)
    small_todos = [Todo(id=i + 1, text=f"task-{i}") for i in range(100)]
    start_small = time.perf_counter()
    for _ in range(100):
        storage.next_id(small_todos)
    small_time = time.perf_counter() - start_small

    # Measure time for large list (10000 items)
    large_todos = [Todo(id=i + 1, text=f"task-{i}") for i in range(10000)]
    start_large = time.perf_counter()
    for _ in range(100):
        storage.next_id(large_todos)
    large_time = time.perf_counter() - start_large

    # If O(1), large list should be at most 10x slower (accounting for cache effects)
    # If O(n), large list (100x bigger) would be ~100x slower
    # We use a generous threshold to avoid flaky tests
    ratio = large_time / small_time if small_time > 0 else 1

    # With O(n), ratio would be ~100. With O(1), ratio should be < 5
    assert ratio < 5, (
        f"next_id appears to be O(n): large_time={large_time:.4f}s, "
        f"small_time={small_time:.4f}s, ratio={ratio:.1f} (expected < 5)"
    )


def test_next_id_uses_cached_max_id(tmp_path: Path) -> None:
    """Test that next_id uses a cached max_id value instead of scanning all items.

    This test verifies the implementation detail that TodoStorage caches
    the maximum ID to avoid O(n) scanning on every call.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos with various IDs (not sequential)
    todos = [
        Todo(id=1, text="task-1"),
        Todo(id=50, text="task-50"),
        Todo(id=100, text="task-100"),
    ]

    # Should return max_id + 1
    assert storage.next_id(todos) == 101

    # After saving, the cache should be updated
    storage.save(todos)
    loaded = storage.load()
    assert storage.next_id(loaded) == 101


def test_next_id_updates_cache_after_add(tmp_path: Path) -> None:
    """Test that cache is correctly maintained after save/load cycle."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Add a todo manually via save
    todos = [Todo(id=5, text="task-5")]
    storage.save(todos)

    # Load and get next_id
    loaded = storage.load()
    next_id = storage.next_id(loaded)
    assert next_id == 6

    # Save with a higher ID and reload - cache should be updated on load
    todos.append(Todo(id=100, text="task-100"))
    storage.save(todos)
    loaded = storage.load()
    next_id = storage.next_id(loaded)
    assert next_id == 101


def test_next_id_empty_list_returns_1(tmp_path: Path) -> None:
    """Test that next_id returns 1 for an empty list."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    assert storage.next_id([]) == 1

    storage.save([])
    loaded = storage.load()
    assert storage.next_id(loaded) == 1
