"""Unit tests for TodoStorage.next_id edge cases."""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list_returns_1() -> None:
    """Empty list should return 1 as the first ID."""
    storage = TodoStorage()
    assert storage.next_id([]) == 1


def test_next_id_single_element() -> None:
    """Single element list should return max_id + 1."""
    storage = TodoStorage()
    todos = [Todo(id=5, text="single")]
    assert storage.next_id(todos) == 6


def test_next_id_non_sequential_ids() -> None:
    """Non-sequential IDs should return max + 1."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first"), Todo(id=100, text="second")]
    assert storage.next_id(todos) == 101


def test_next_id_sequential_ids() -> None:
    """Sequential IDs should return max + 1."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]
    assert storage.next_id(todos) == 4


def test_next_id_with_id_zero() -> None:
    """List with id=0 should return 1."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="zero")]
    assert storage.next_id(todos) == 1


def test_next_id_large_id() -> None:
    """Large ID values should work correctly."""
    storage = TodoStorage()
    todos = [Todo(id=999999999, text="large")]
    assert storage.next_id(todos) == 1000000000
