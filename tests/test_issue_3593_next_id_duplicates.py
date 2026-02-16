"""Regression test for issue #3593: next_id() duplicate ID generation bug.

Bug: next_id() can generate duplicate IDs when todo list contains duplicate IDs.
Location: src/flywheel/storage.py:128
Original code: return (max((todo.id for todo in todos), default=0) + 1) if todos else 1

The issue: max() only finds the maximum value but doesn't check if that ID
already exists. If the list has duplicate IDs, the new ID could clash with
existing ones.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_duplicate_ids_returns_unique() -> None:
    """Bug #3593: next_id() should return unique ID even with duplicates.

    When the todo list contains duplicate IDs (which shouldn't happen
    in normal use but can occur due to data corruption or bugs),
    next_id() should still return an ID that doesn't conflict.
    """
    storage = TodoStorage()
    # Two todos with same ID - this simulates data corruption
    todos = [Todo(id=1, text="first"), Todo(id=1, text="duplicate")]

    # next_id should return 2, not a duplicate of 1
    new_id = storage.next_id(todos)
    assert new_id == 2, f"Expected next_id=2 but got {new_id}"


def test_next_id_with_gap_ids_returns_max_plus_one() -> None:
    """Verify next_id returns max + 1 even when there are gaps."""
    storage = TodoStorage()
    # Non-contiguous IDs: 3 and 5
    todos = [Todo(id=3, text="a"), Todo(id=5, text="b")]

    new_id = storage.next_id(todos)
    assert new_id == 6, f"Expected next_id=6 but got {new_id}"


def test_next_id_with_empty_list_returns_one() -> None:
    """Verify next_id returns 1 for empty list."""
    storage = TodoStorage()
    todos: list[Todo] = []

    new_id = storage.next_id(todos)
    assert new_id == 1, f"Expected next_id=1 but got {new_id}"


def test_next_id_uses_set_for_uniqueness() -> None:
    """Verify that next_id properly handles multiple duplicate scenarios."""
    storage = TodoStorage()

    # Multiple duplicates of the same ID
    todos = [Todo(id=5, text=f"item-{i}") for i in range(5)]
    assert storage.next_id(todos) == 6

    # Mixed duplicates
    todos = [Todo(id=1, text="a"), Todo(id=1, text="b"), Todo(id=2, text="c")]
    assert storage.next_id(todos) == 3

    # All same ID with high value
    todos = [Todo(id=100, text="x"), Todo(id=100, text="y")]
    assert storage.next_id(todos) == 101
