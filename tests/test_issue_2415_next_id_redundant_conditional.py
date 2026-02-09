"""Tests for issue #2415: next_id() contains redundant conditional logic.

The issue identifies that the `if todos else 1` conditional in next_id() is redundant
because `max(..., default=0) + 1` already returns 1 for an empty list.

This test file verifies that next_id() works correctly for all edge cases.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list_returns_1() -> None:
    """Issue #2415: next_id([]) should return 1."""
    storage = TodoStorage()
    assert storage.next_id([]) == 1


def test_next_id_single_todo_returns_2() -> None:
    """Issue #2415: next_id([Todo(id=1)]) should return 2."""
    storage = TodoStorage()
    assert storage.next_id([Todo(id=1, text="test")]) == 2


def test_next_id_multiple_todos_returns_max_plus_one() -> None:
    """Issue #2415: next_id([Todo(id=1), Todo(id=2)]) should return 3."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=2, text="b")]
    assert storage.next_id(todos) == 3


def test_next_id_non_contiguous_ids() -> None:
    """Issue #2415: next_id should work with non-contiguous IDs."""
    storage = TodoStorage()
    # IDs with gaps - should still return max + 1
    todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=10, text="c")]
    assert storage.next_id(todos) == 11
