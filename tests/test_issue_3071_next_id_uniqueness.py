"""Regression test for issue #3071: next_id() should return unique IDs.

When stored JSON contains duplicate todo IDs, next_id() must still return
an ID that does not collide with any existing todo, not just the max+1.

The issue: next_id() uses max() which doesn't account for duplicates.
If todos have IDs [1, 1, 3], max() returns 3, so next_id() returns 4.
But if we use the smallest unused approach, it should return 2.

Either approach is valid, but we must ensure the returned ID is NOT
already in use by ANY todo in the list.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_duplicate_ids_returns_unused_id() -> None:
    """next_id() must return an ID not used by any todo in the list.

    When JSON contains duplicate IDs (e.g., due to corruption or bug),
    next_id() should still return a unique ID.
    """
    storage = TodoStorage(":memory:")  # Path doesn't matter for next_id

    # Simulate corrupted data with duplicate IDs [1, 1, 3]
    todos = [
        Todo(id=1, text="first"),
        Todo(id=1, text="duplicate of first"),  # Duplicate ID!
        Todo(id=3, text="third"),
    ]

    # next_id() should return an ID that's not in the existing set
    # Existing IDs: {1, 3}
    # Smallest unused positive integer: 2
    next_id = storage.next_id(todos)

    # The returned ID must not collide with any existing todo
    existing_ids = {todo.id for todo in todos}
    assert next_id not in existing_ids, (
        f"next_id() returned {next_id} which collides with existing IDs {existing_ids}"
    )


def test_next_id_returns_smallest_unused_positive_integer() -> None:
    """next_id() should return the smallest unused positive integer.

    This is the expected behavior for a clean ID allocation strategy.
    """
    storage = TodoStorage(":memory:")

    # IDs [1, 3] -> smallest unused is 2
    todos = [
        Todo(id=1, text="first"),
        Todo(id=3, text="third"),
    ]
    assert storage.next_id(todos) == 2

    # IDs [1, 2, 3] -> smallest unused is 4
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]
    assert storage.next_id(todos) == 4

    # IDs [2, 4] -> smallest unused is 1
    todos = [
        Todo(id=2, text="second"),
        Todo(id=4, text="fourth"),
    ]
    assert storage.next_id(todos) == 1


def test_next_id_with_all_duplicate_ids() -> None:
    """next_id() should work even when all todos have the same duplicate ID."""
    storage = TodoStorage(":memory:")

    # All todos have ID 5
    todos = [
        Todo(id=5, text="first"),
        Todo(id=5, text="second"),
        Todo(id=5, text="third"),
    ]

    next_id = storage.next_id(todos)

    # Should return 1 (smallest unused) since 5 is the only existing ID
    assert next_id == 1, f"Expected 1, got {next_id}"


def test_next_id_preserves_backward_compatibility() -> None:
    """next_id() should still work correctly with normal sequential IDs."""
    storage = TodoStorage(":memory:")

    # Empty list -> should return 1
    assert storage.next_id([]) == 1

    # [1] -> should return 2
    todos = [Todo(id=1, text="first")]
    assert storage.next_id(todos) == 2

    # [1, 2, 3] -> should return 4
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]
    assert storage.next_id(todos) == 4
