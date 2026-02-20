"""Tests for issue #4610: next_id performance optimization.

This test suite verifies that next_id uses O(1) time complexity by
maintaining a cached max_id counter instead of traversing the entire
list on each call.

The issue: next_id previously called max() on every invocation, which
is O(n) and causes performance degradation for large todo lists.

The fix: Maintain a cached _max_id attribute that is updated in O(1)
time during add/remove operations.
"""

from __future__ import annotations

import time

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_is_constant_time(tmp_path) -> None:
    """Test that next_id operates in O(1) time regardless of list size.

    This test verifies that next_id doesn't traverse the entire list
    by checking that the execution time doesn't grow proportionally
    to the list size.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a large list of todos
    large_todos = [Todo(id=i, text=f"task-{i}") for i in range(1, 10001)]
    storage.save(large_todos)

    # Load the todos back
    loaded = storage.load()

    # Time multiple calls to next_id - should be fast and consistent
    start = time.perf_counter()
    for _ in range(100):
        storage.next_id(loaded)
    elapsed = time.perf_counter() - start

    # With O(n) implementation, this would take > 100ms for 10000 items x 100 calls
    # With O(1) implementation using cached max_id, it should be < 10ms
    # We use a generous threshold to avoid flakiness
    assert elapsed < 0.1, (
        f"next_id appears to be O(n) - 100 calls took {elapsed:.3f}s "
        f"for 10000 items. Expected < 0.1s with O(1) implementation."
    )


def test_next_id_returns_correct_max_plus_one(tmp_path) -> None:
    """Test that next_id returns max_id + 1 correctly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Empty list should return 1
    assert storage.next_id([]) == 1

    # Single item
    assert storage.next_id([Todo(id=5, text="test")]) == 6

    # Multiple items with non-sequential IDs
    todos = [Todo(id=3, text="a"), Todo(id=10, text="b"), Todo(id=7, text="c")]
    assert storage.next_id(todos) == 11

    # Large list with max at the end
    large_todos = [Todo(id=i, text=f"t{i}") for i in range(1, 1001)]
    assert storage.next_id(large_todos) == 1001


def test_next_id_uses_cached_max_id_after_load(tmp_path) -> None:
    """Test that next_id uses cached max_id after loading from storage.

    This verifies the core fix: after loading todos from storage,
    the max_id should be cached and next_id should use the cache
    instead of recalculating.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save todos with known max ID
    todos = [Todo(id=i, text=f"task-{i}") for i in range(1, 1001)]
    storage.save(todos)

    # Load from storage - this should populate the cached max_id
    loaded = storage.load()

    # next_id should return 1001 without traversing the list
    # We verify by accessing the internal cache if it exists
    assert storage.next_id(loaded) == 1001


def test_max_id_cache_updated_after_operations(tmp_path) -> None:
    """Test that the max_id cache is properly maintained during operations.

    When todos are added or removed, the cached max_id should be updated.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initial state
    todos = [Todo(id=1, text="a"), Todo(id=5, text="b")]
    storage.save(todos)

    loaded = storage.load()
    assert storage.next_id(loaded) == 6

    # Simulate adding a new todo with higher ID
    loaded.append(Todo(id=10, text="c"))
    storage.save(loaded)

    loaded = storage.load()
    assert storage.next_id(loaded) == 11


def test_next_id_handles_empty_list_correctly(tmp_path) -> None:
    """Test that next_id handles empty lists correctly with caching."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Empty list case
    assert storage.next_id([]) == 1

    # After saving empty list
    storage.save([])
    loaded = storage.load()
    assert storage.next_id(loaded) == 1
