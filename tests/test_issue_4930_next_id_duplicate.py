"""Tests for issue #4930: next_id should not generate duplicate IDs.

This test suite verifies that next_id never returns an ID that already exists
in the todos list, even when loaded data contains non-sequential or negative IDs.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_non_sequential_ids() -> None:
    """Test that next_id returns smallest unused ID for non-sequential existing IDs.

    Example: IDs [1, 5, 10] should return next_id=2 (smallest unused positive integer)
    This is more efficient than returning 11 (max+1).
    """
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=10, text="c")]

    next_id = storage.next_id(todos)
    # With the fix, should return 2 (smallest unused positive integer)
    assert next_id == 2, f"Expected next_id=2 for IDs [1,5,10], got {next_id}"
    assert next_id not in [todo.id for todo in todos], (
        f"next_id={next_id} collides with existing ID"
    )


def test_next_id_with_sequential_ids() -> None:
    """Test that next_id returns correct ID for sequential existing IDs.

    Example: IDs [1, 2, 3] should return next_id=4 (current behavior - OK)
    """
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]

    next_id = storage.next_id(todos)
    assert next_id == 4, f"Expected next_id=4 for IDs [1,2,3], got {next_id}"


def test_next_id_no_collision_with_negative_ids() -> None:
    """Test that negative IDs don't cause collisions.

    Example: IDs [1, -1, 5] should not return 2 (collision risk).
    The fix should ensure next_id doesn't collide with existing positive IDs.
    """
    storage = TodoStorage()
    # Note: from_dict allows negative IDs currently, but next_id should handle them
    todos = [Todo(id=1, text="a"), Todo(id=-1, text="b"), Todo(id=5, text="c")]

    next_id = storage.next_id(todos)
    # Should not return 1 (exists), -1 (negative), 5 (exists)
    # Should return the smallest unused positive integer >= 2
    assert next_id not in [todo.id for todo in todos], (
        f"next_id={next_id} collides with existing ID"
    )
    assert next_id > 0, f"next_id={next_id} should be positive"


def test_next_id_avoids_duplicate_with_gap() -> None:
    """Test that next_id doesn't return an ID that already exists in a gap.

    Example: IDs [1, 3] - current max+1=4 is fine, but should work for any case.
    This test verifies the core fix: next_id must not return an existing ID.
    """
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=3, text="c")]

    next_id = storage.next_id(todos)
    # Should not return 1 or 3
    assert next_id not in [todo.id for todo in todos], (
        f"next_id={next_id} collides with existing ID"
    )


def test_next_id_empty_list() -> None:
    """Test that next_id returns 1 for empty list."""
    storage = TodoStorage()
    todos: list[Todo] = []

    next_id = storage.next_id(todos)
    assert next_id == 1, f"Expected next_id=1 for empty list, got {next_id}"


def test_next_id_with_zero_id() -> None:
    """Test that ID=0 is handled correctly.

    ID=0 is a valid integer but should be treated like any other existing ID.
    """
    storage = TodoStorage()
    todos = [Todo(id=0, text="a"), Todo(id=1, text="b")]

    next_id = storage.next_id(todos)
    # Should not return 0 or 1
    assert next_id not in [todo.id for todo in todos], (
        f"next_id={next_id} collides with existing ID"
    )
    assert next_id > 0, f"next_id={next_id} should be positive"


def test_next_id_finds_smallest_unused() -> None:
    """Test that next_id finds the smallest unused positive integer.

    This is the recommended fix: find smallest unused positive integer.
    Example: IDs [1, 3, 5] -> smallest unused is 2, not 6.
    """
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=3, text="b"), Todo(id=5, text="c")]

    next_id = storage.next_id(todos)
    # With the fix, should return 2 (smallest unused positive integer)
    # Current behavior would return 6 (max+1)
    assert next_id == 2, f"Expected next_id=2 (smallest unused), got {next_id}"
    assert next_id not in [todo.id for todo in todos], (
        f"next_id={next_id} collides with existing ID"
    )


def test_next_id_all_negative_ids() -> None:
    """Test that all negative IDs still returns a positive next_id."""
    storage = TodoStorage()
    todos = [Todo(id=-5, text="a"), Todo(id=-1, text="b")]

    next_id = storage.next_id(todos)
    assert next_id == 1, f"Expected next_id=1 when all IDs are negative, got {next_id}"
    assert next_id > 0, f"next_id={next_id} should be positive"
