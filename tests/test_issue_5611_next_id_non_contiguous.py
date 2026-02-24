"""Regression test for issue #5611: next_id() should return unique IDs with gaps.

Tests that next_id() returns a unique ID that doesn't collide with existing IDs
even when there are gaps in the ID sequence.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_first_available_when_gaps_exist() -> None:
    """Bug #5611: next_id() should return the first available ID, not max+1.

    When todos have non-contiguous IDs (e.g., due to deletions), next_id()
    should return the first available ID rather than always returning max+1.
    This prevents ID collisions when items are deleted and new ones are added.
    """
    storage = TodoStorage("/tmp/test.json")  # Path doesn't matter for this test

    # Create todos with gaps: [1, 3, 5]
    todos = [
        Todo(id=1, text="first"),
        Todo(id=3, text="third"),
        Todo(id=5, text="fifth"),
    ]

    # next_id() should return 2 (first available), not 6 (max+1)
    next_id = storage.next_id(todos)
    assert next_id == 2, f"Expected next_id=2 (first available), got {next_id}"


def test_next_id_fills_gaps_in_sequence() -> None:
    """Verify next_id() fills gaps in the ID sequence."""
    storage = TodoStorage("/tmp/test.json")

    # Create todos: [1, 2, 4] - gap at 3
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=4, text="fourth"),
    ]

    # next_id() should return 3 (the gap), not 5
    next_id = storage.next_id(todos)
    assert next_id == 3, f"Expected next_id=3 (filling gap), got {next_id}"


def test_next_id_no_collision_with_existing_ids() -> None:
    """Ensure next_id() never returns an ID that already exists."""
    storage = TodoStorage("/tmp/test.json")

    # Various gap patterns
    test_cases = [
        [Todo(id=1, text="a"), Todo(id=3, text="b")],  # gap at 2
        [Todo(id=2, text="a"), Todo(id=4, text="b")],  # gap at 1, 3
        [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=10, text="c")],  # gaps at 3-9
    ]

    for todos in test_cases:
        existing_ids = {todo.id for todo in todos}
        next_id = storage.next_id(todos)
        assert next_id not in existing_ids, (
            f"next_id={next_id} collides with existing IDs {existing_ids}"
        )


def test_next_id_returns_1_for_empty_list() -> None:
    """next_id() should return 1 for an empty todo list."""
    storage = TodoStorage("/tmp/test.json")

    next_id = storage.next_id([])
    assert next_id == 1, f"Expected next_id=1 for empty list, got {next_id}"


def test_next_id_returns_next_after_contiguous() -> None:
    """next_id() should return max+1 when IDs are contiguous."""
    storage = TodoStorage("/tmp/test.json")

    # Contiguous IDs: [1, 2, 3]
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]

    next_id = storage.next_id(todos)
    assert next_id == 4, f"Expected next_id=4 (max+1), got {next_id}"
