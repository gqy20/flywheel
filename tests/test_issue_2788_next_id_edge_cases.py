"""Tests for next_id() edge cases.

Bug #2788: next_id() returns different values for empty vs non-empty list with max id 0.
The original code had a redundant ternary operator that was confusing.

Acceptance criteria:
- next_id([]) returns 1
- next_id([Todo(id=0, text='x')]) returns 1
- next_id([Todo(id=1, text='x')]) returns 2
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_1_for_empty_list() -> None:
    """Bug #2788: Empty list should return next_id of 1."""
    storage = TodoStorage()
    assert storage.next_id([]) == 1


def test_next_id_returns_1_for_list_with_id_0() -> None:
    """Bug #2788: List with id=0 should return next_id of 1.

    This is the key edge case - when the max id is 0, we should still
    return 1 (not 2 or something else).
    """
    storage = TodoStorage()
    todos = [Todo(id=0, text="x")]
    assert storage.next_id(todos) == 1


def test_next_id_returns_2_for_list_with_id_1() -> None:
    """Bug #2788: List with id=1 should return next_id of 2."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="x")]
    assert storage.next_id(todos) == 2


def test_next_id_returns_max_plus_one_for_multiple_todos() -> None:
    """Bug #2788: Multiple todos should return max id + 1."""
    storage = TodoStorage()

    # Todos with ids 1, 2, 3 -> next should be 4
    todos = [
        Todo(id=1, text="a"),
        Todo(id=2, text="b"),
        Todo(id=3, text="c"),
    ]
    assert storage.next_id(todos) == 4

    # Todos with ids 0, 5, 10 -> next should be 11
    todos = [
        Todo(id=0, text="x"),
        Todo(id=5, text="y"),
        Todo(id=10, text="z"),
    ]
    assert storage.next_id(todos) == 11
