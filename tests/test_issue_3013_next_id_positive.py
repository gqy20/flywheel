"""Regression tests for issue #3013: next_id returns negative or zero IDs.

Bug: next_id returns negative or zero IDs when existing todo IDs are negative or zero.
Fix: Ensure next_id always returns a positive integer (minimum 1).
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_negative_id_returns_1() -> None:
    """Bug #3013: next_id([Todo(id=-5, ...)]) should return 1, not -4."""
    storage = TodoStorage()
    todos = [Todo(id=-5, text="negative id")]
    assert storage.next_id(todos) == 1


def test_next_id_with_zero_id_returns_1() -> None:
    """Bug #3013: next_id([Todo(id=0, ...)]) should return 1."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="zero id")]
    assert storage.next_id(todos) == 1


def test_next_id_with_positive_id_returns_max_plus_1() -> None:
    """Verify normal case: next_id([Todo(id=5, ...)]) should return 6."""
    storage = TodoStorage()
    todos = [Todo(id=5, text="positive id")]
    assert storage.next_id(todos) == 6


def test_next_id_with_empty_list_returns_1() -> None:
    """Verify edge case: next_id([]) should return 1."""
    storage = TodoStorage()
    assert storage.next_id([]) == 1


def test_next_id_with_mixed_ids_returns_max_positive_plus_1() -> None:
    """Bug #3013: Mixed ids including negative should return max positive + 1."""
    storage = TodoStorage()
    todos = [
        Todo(id=-5, text="negative id"),
        Todo(id=0, text="zero id"),
        Todo(id=3, text="positive id"),
    ]
    assert storage.next_id(todos) == 4


def test_next_id_with_all_negative_ids_returns_1() -> None:
    """Bug #3013: All negative ids should return 1."""
    storage = TodoStorage()
    todos = [
        Todo(id=-1, text="first negative"),
        Todo(id=-10, text="second negative"),
        Todo(id=-3, text="third negative"),
    ]
    assert storage.next_id(todos) == 1
