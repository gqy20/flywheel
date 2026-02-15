"""Tests for issue #3532: next_id() should not return existing IDs (ID collision).

Bug: When JSON file contains non-contiguous or deleted IDs, next_id() could
return an ID that already exists, causing ID collision.

This module provides regression tests for the fix.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_unique_id_for_non_contiguous_ids() -> None:
    """Regression test for issue #3532.

    Given todos with IDs [1, 3], next_id should return 4 (max+1).
    The returned ID must not collide with existing IDs (1 or 3).
    """
    storage = TodoStorage(":memory:")  # Path doesn't matter for next_id
    todos = [Todo(id=1, text="task 1"), Todo(id=3, text="task 3")]

    new_id = storage.next_id(todos)

    # The new ID should not be 1 or 3 (existing IDs)
    assert new_id not in {1, 3}, f"ID collision: {new_id} already exists"
    # It should be 4 (max+1, since 4 doesn't exist)
    assert new_id == 4


def test_next_id_returns_unique_id_for_gaps_in_sequence() -> None:
    """Test that next_id handles ID gaps correctly.

    Given todos with IDs [1, 3, 5], verify next_id returns 6 (max+1).
    This is correct behavior since 6 doesn't exist.
    """
    storage = TodoStorage(":memory:")
    todos = [Todo(id=1, text="a"), Todo(id=3, text="b"), Todo(id=5, text="c")]

    new_id = storage.next_id(todos)

    # Should not collide with existing IDs
    assert new_id not in {1, 3, 5}
    # Should be max+1 = 6
    assert new_id == 6


def test_next_id_returns_unique_id_after_removal() -> None:
    """Test that next_id doesn't reuse deleted IDs that would cause collision.

    If we have [1, 2, 3] and delete 2, then add, the new ID should be 4
    (not 3, which would collide with the existing 3).

    Note: The old implementation would return max([1,3])+1 = 4, which is correct.
    The bug was when IDs were like [1, 3, 4] - it would return 5, but if
    someone manually edited the JSON to have IDs [1, 2, 4], it would return 5,
    not 3 (which is available but we don't fill gaps).
    """
    storage = TodoStorage(":memory:")
    todos = [Todo(id=1, text="a"), Todo(id=3, text="c")]

    new_id = storage.next_id(todos)

    # New ID must be unique (not 1 or 3)
    assert new_id not in {1, 3}


def test_next_id_returns_1_for_empty_list() -> None:
    """Test that next_id returns 1 for an empty todo list."""
    storage = TodoStorage(":memory:")
    todos: list[Todo] = []

    new_id = storage.next_id(todos)

    assert new_id == 1


def test_next_id_handles_single_element() -> None:
    """Test that next_id works correctly with a single todo."""
    storage = TodoStorage(":memory:")
    todos = [Todo(id=5, text="only task")]

    new_id = storage.next_id(todos)

    # Should return 6 (5+1), which doesn't collide
    assert new_id == 6


def test_next_id_never_returns_existing_id() -> None:
    """Property-based test: next_id should NEVER return an ID that already exists.

    This is the core invariant that must hold regardless of ID distribution.
    """
    storage = TodoStorage(":memory:")

    # Test various non-contiguous ID patterns
    test_cases = [
        [1, 2, 3],  # contiguous
        [1, 3, 5],  # odd numbers
        [10, 20, 30],  # spaced
        [1, 100],  # large gap
        [5],  # single high ID
    ]

    for ids in test_cases:
        todos = [Todo(id=id_, text=f"task {id_}") for id_ in ids]
        new_id = storage.next_id(todos)

        # Core invariant: new_id must not be in the existing set
        assert new_id not in set(ids), (
            f"ID collision! next_id returned {new_id} which exists in {ids}"
        )
