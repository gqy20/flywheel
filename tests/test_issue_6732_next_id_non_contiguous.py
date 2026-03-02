"""Test for issue #6732: next_id should return smallest unused ID.

Bug: When todos have non-contiguous IDs (e.g., [1, 5]), next_id was returning
max+1 (6) instead of finding the smallest unused ID (2).
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_smallest_unused_for_non_contiguous_ids() -> None:
    """Issue #6732: next_id should return the smallest unused ID.

    When todos have non-contiguous IDs like [1, 3, 5], next_id should
    return 2 (the smallest unused ID), not 6 (max+1).
    """
    storage = TodoStorage()

    # Create todos with non-contiguous IDs [1, 3, 5]
    todos = [
        Todo(id=1, text="first"),
        Todo(id=3, text="third"),
        Todo(id=5, text="fifth"),
    ]

    # next_id should return 2 (smallest unused), not 6
    assert storage.next_id(todos) == 2


def test_next_id_fills_gap_in_middle() -> None:
    """Verify next_id fills gaps in the middle of ID range.

    If we have [1, 2, 4], next_id should return 3.
    """
    storage = TodoStorage()

    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=4, text="fourth"),
    ]

    assert storage.next_id(todos) == 3


def test_next_id_returns_max_plus_one_when_no_gaps() -> None:
    """Verify next_id still works correctly for contiguous IDs.

    If we have [1, 2, 3], next_id should return 4.
    """
    storage = TodoStorage()

    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]

    assert storage.next_id(todos) == 4


def test_next_id_returns_1_for_empty_list() -> None:
    """Verify next_id returns 1 when there are no todos."""
    storage = TodoStorage()

    assert storage.next_id([]) == 1


def test_next_id_handles_single_gap_at_start() -> None:
    """Verify next_id handles case where ID 1 is missing.

    If we have [2, 3], next_id should return 1.
    """
    storage = TodoStorage()

    todos = [
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]

    assert storage.next_id(todos) == 1


def test_next_id_handles_large_gap() -> None:
    """Verify next_id handles large gaps in IDs.

    If we have [1, 100], next_id should return 2.
    """
    storage = TodoStorage()

    todos = [
        Todo(id=1, text="first"),
        Todo(id=100, text="hundredth"),
    ]

    assert storage.next_id(todos) == 2
