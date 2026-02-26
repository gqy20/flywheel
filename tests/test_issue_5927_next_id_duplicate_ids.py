"""Regression test for issue #5927: next_id with duplicate IDs.

This test ensures that next_id correctly handles duplicate IDs in the todo list
by returning a unique ID that doesn't conflict with any existing IDs.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_duplicate_ids_returns_correct_value() -> None:
    """Test that next_id returns correct value when there are duplicate IDs.

    When todos have duplicate IDs like [1, 1, 3], next_id should return 4
    (max unique ID + 1), not a conflicting ID.
    """
    storage = TodoStorage()

    # Create todos with duplicate IDs
    todos = [
        Todo(id=1, text="first"),
        Todo(id=1, text="duplicate of first"),
        Todo(id=3, text="third"),
    ]

    # next_id should return 4 (max unique ID is 3, so 3+1=4)
    new_id = storage.next_id(todos)
    assert new_id == 4


def test_next_id_with_all_duplicate_ids() -> None:
    """Test that next_id works when all IDs are duplicates.

    When all todos have the same ID, next_id should still return a valid unique ID.
    """
    storage = TodoStorage()

    # All todos have ID 5
    todos = [
        Todo(id=5, text="first"),
        Todo(id=5, text="second"),
        Todo(id=5, text="third"),
    ]

    # next_id should return 6 (max unique ID is 5, so 5+1=6)
    new_id = storage.next_id(todos)
    assert new_id == 6


def test_next_id_with_sequential_duplicates() -> None:
    """Test next_id with sequential duplicate IDs.

    Case: [1, 2, 2, 3, 3, 3] should return 4.
    """
    storage = TodoStorage()

    todos = [
        Todo(id=1, text="one"),
        Todo(id=2, text="two-a"),
        Todo(id=2, text="two-b"),
        Todo(id=3, text="three-a"),
        Todo(id=3, text="three-b"),
        Todo(id=3, text="three-c"),
    ]

    new_id = storage.next_id(todos)
    assert new_id == 4


def test_next_id_empty_list_returns_one() -> None:
    """Test that empty list returns 1."""
    storage = TodoStorage()

    new_id = storage.next_id([])
    assert new_id == 1


def test_next_id_single_element_returns_two() -> None:
    """Test that single element returns id+1."""
    storage = TodoStorage()

    todos = [Todo(id=1, text="only")]
    new_id = storage.next_id(todos)
    assert new_id == 2
