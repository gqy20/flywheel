"""Regression test for issue #3071: next_id() duplicate ID bug.

Issue: next_id() can return duplicate/non-unique IDs when stored JSON
contains duplicate todo IDs. The original implementation used max() which
doesn't detect duplicates in the existing list.

The fix ensures next_id() returns the smallest unused positive integer
that is not already in the existing set of IDs.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_unique_id_when_duplicates_exist() -> None:
    """Test that next_id() returns a unique ID not in existing set.

    When the todos list has duplicate IDs (e.g., [1, 1, 3]), next_id()
    should return 2 (the smallest unused positive integer) rather than
    returning a duplicate.
    """
    storage = TodoStorage("/tmp/test.json")  # Path doesn't matter for next_id()

    # Create todos with duplicate IDs: [1, 1, 3]
    todos = [
        Todo(id=1, text="first"),
        Todo(id=1, text="duplicate of first"),
        Todo(id=3, text="third"),
    ]

    # next_id() should return 2 (smallest unused), not 4 (max+1 that would collide)
    new_id = storage.next_id(todos)

    # The new ID must not be in the existing set
    existing_ids = {todo.id for todo in todos}
    assert new_id not in existing_ids, (
        f"next_id() returned {new_id} which already exists in {existing_ids}"
    )

    # Specifically, it should return 2 (the smallest unused positive integer)
    assert new_id == 2, f"Expected 2 (smallest unused), got {new_id}"


def test_next_id_returns_one_for_empty_list() -> None:
    """Test that next_id() returns 1 for an empty list."""
    storage = TodoStorage("/tmp/test.json")

    new_id = storage.next_id([])

    assert new_id == 1, f"Expected 1 for empty list, got {new_id}"


def test_next_id_returns_max_plus_one_when_no_gaps() -> None:
    """Test that next_id() returns max+1 when there are no gaps."""
    storage = TodoStorage("/tmp/test.json")

    # IDs [1, 2, 3] - no gaps
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]

    new_id = storage.next_id(todos)

    assert new_id == 4, f"Expected 4 (max+1), got {new_id}"


def test_next_id_fills_gap_in_sequence() -> None:
    """Test that next_id() fills gaps in the ID sequence."""
    storage = TodoStorage("/tmp/test.json")

    # IDs [1, 3, 5] - gaps at 2 and 4
    todos = [
        Todo(id=1, text="first"),
        Todo(id=3, text="third"),
        Todo(id=5, text="fifth"),
    ]

    new_id = storage.next_id(todos)

    # Should return 2 (smallest unused)
    assert new_id == 2, f"Expected 2 (smallest gap), got {new_id}"


def test_next_id_handles_multiple_duplicates() -> None:
    """Test that next_id() handles multiple duplicate IDs correctly."""
    storage = TodoStorage("/tmp/test.json")

    # Multiple duplicates: [1, 1, 1, 2, 2, 5]
    todos = [
        Todo(id=1, text="first"),
        Todo(id=1, text="dup1"),
        Todo(id=1, text="dup2"),
        Todo(id=2, text="second"),
        Todo(id=2, text="dup of second"),
        Todo(id=5, text="fifth"),
    ]

    new_id = storage.next_id(todos)

    # Should return 3 (smallest unused)
    existing_ids = {todo.id for todo in todos}
    assert new_id not in existing_ids, (
        f"next_id() returned {new_id} which already exists in {existing_ids}"
    )
    assert new_id == 3, f"Expected 3 (smallest unused), got {new_id}"
