"""Regression test for issue #4453: next_id() should handle duplicate IDs.

The issue reported that next_id() does not check for duplicate IDs in existing todos.
According to the acceptance criteria, next_id() should return max(unique_ids) + 1,
ensuring it works correctly even when duplicates exist in the todo list.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_duplicate_ids_returns_max_plus_one() -> None:
    """Bug #4453: next_id() should return max(unique_ids) + 1 even with duplicates.

    When todos contain duplicate IDs (e.g., from manual JSON edits),
    next_id() should use the maximum unique ID value, not be affected
    by the duplicates.
    """
    storage = TodoStorage()

    # Create todos with duplicate IDs (e.g., ID 1 appears twice)
    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=1, text="second todo with duplicate ID"),
        Todo(id=3, text="third todo"),
    ]

    # next_id should return 4 (max of unique IDs [1, 3] is 3, + 1 = 4)
    assert storage.next_id(todos) == 4


def test_next_id_with_all_duplicate_ids() -> None:
    """Bug #4453: next_id() should handle case where all IDs are duplicates."""
    storage = TodoStorage()

    # All todos have the same ID
    todos = [
        Todo(id=2, text="first"),
        Todo(id=2, text="second"),
        Todo(id=2, text="third"),
    ]

    # next_id should return 3 (max unique ID is 2, + 1 = 3)
    assert storage.next_id(todos) == 3


def test_next_id_with_gaps_still_returns_max_plus_one() -> None:
    """Bug #4453: next_id() should return max+1, not fill gaps.

    This documents current behavior: with gaps in IDs, next_id returns
    max+1, not the smallest unused positive integer.
    """
    storage = TodoStorage()

    # Todos with a gap (ID 2 is missing)
    todos = [
        Todo(id=1, text="first"),
        Todo(id=3, text="third"),
    ]

    # next_id returns 4 (max is 3, + 1 = 4), NOT 2 to fill the gap
    assert storage.next_id(todos) == 4


def test_next_id_empty_list_returns_one() -> None:
    """Bug #4453: next_id() should return 1 for empty list."""
    storage = TodoStorage()

    # Empty list should return 1
    assert storage.next_id([]) == 1
