"""Tests for issue #5376: next_id() may return duplicate ID when todos have non-contiguous IDs.

This test suite verifies that next_id() returns a unique ID that doesn't collide
with any existing todo IDs, even when the IDs are non-contiguous.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_non_contiguous_ids() -> None:
    """Test that next_id returns max+1 for non-contiguous IDs."""
    storage = TodoStorage()
    # Create todos with IDs [1, 5, 10]
    todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=10, text="c")]

    # next_id should return 11 (max+1), not a value that might collide
    assert storage.next_id(todos) == 11


def test_next_id_never_returns_existing_id() -> None:
    """Test that next_id never returns an ID that already exists in the list."""
    storage = TodoStorage()

    # Create todos with non-contiguous IDs [1, 3, 7]
    todos = [Todo(id=1, text="a"), Todo(id=3, text="b"), Todo(id=7, text="c")]

    # The returned ID should not be any existing ID
    new_id = storage.next_id(todos)
    existing_ids = {todo.id for todo in todos}
    assert new_id not in existing_ids, f"next_id returned {new_id} which already exists"


def test_next_id_after_deletion() -> None:
    """Test that next_id works correctly after simulating a deletion (gap in IDs).

    This simulates: add todo, remove it, add new todo - verify IDs are unique.
    """
    storage = TodoStorage()

    # Simulate: had IDs 1, 2, 3 - then deleted ID 2
    # Now have IDs [1, 3]
    todos = [Todo(id=1, text="first"), Todo(id=3, text="third")]

    # next_id should return 4 (max+1), not 2 which would fill the gap
    # (filling the gap could cause issues if we're trying to avoid reuse)
    new_id = storage.next_id(todos)
    assert new_id == 4


def test_next_id_always_greater_than_max() -> None:
    """Test that next_id always returns a value greater than current max ID."""
    storage = TodoStorage()

    # Various non-contiguous patterns
    patterns = [
        [1, 100],  # Large gap
        [50, 51, 52],  # Starting from non-1
        [1, 2, 10, 20, 30],  # Multiple gaps
    ]

    for pattern in patterns:
        todos = [Todo(id=id_, text=f"todo-{id_}") for id_ in pattern]
        max_id = max(pattern)
        new_id = storage.next_id(todos)
        assert new_id > max_id, f"next_id={new_id} should be > max_id={max_id} for pattern {pattern}"


def test_next_id_preserves_uniqueness_with_large_gap() -> None:
    """Test that next_id handles large gaps correctly without collision.

    This tests the scenario where the gap between IDs is very large.
    """
    storage = TodoStorage()

    # Create todos with a large gap: [1, 1000]
    todos = [Todo(id=1, text="first"), Todo(id=1000, text="thousandth")]

    new_id = storage.next_id(todos)

    # Should return 1001, not something that could collide
    assert new_id == 1001
    assert new_id not in {1, 1000}
