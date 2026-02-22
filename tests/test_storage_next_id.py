"""Dedicated tests for TodoStorage.next_id() method covering edge cases."""

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
    todos = [Todo(id=5, text="single todo")]
    assert storage.next_id(todos) == 6


def test_next_id_non_sequential_ids() -> None:
    """Non-sequential IDs should return max_id + 1."""
    storage = TodoStorage()
    todos = [
        Todo(id=1, text="first"),
        Todo(id=100, text="second"),
    ]
    assert storage.next_id(todos) == 101


def test_next_id_sequential_ids() -> None:
    """Sequential IDs should return max_id + 1."""
    storage = TodoStorage()
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]
    assert storage.next_id(todos) == 4


def test_next_id_zero_id() -> None:
    """List with ID 0 should return max_id + 1 (which is 1)."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="zero id todo")]
    assert storage.next_id(todos) == 1


def test_next_id_large_id() -> None:
    """List with large ID should handle correctly without overflow."""
    storage = TodoStorage()
    large_id = 999999999
    todos = [Todo(id=large_id, text="large id todo")]
    assert storage.next_id(todos) == large_id + 1


def test_next_id_negative_id() -> None:
    """List with negative ID should return max_id + 1.

    Note: While negative IDs are unusual, the next_id method uses max()
    which will find the maximum (positive or negative). If all IDs are
    negative, max_id + 1 could be <= 0, but the current implementation
    returns max + 1 regardless.
    """
    storage = TodoStorage()
    todos = [Todo(id=-5, text="negative id todo")]
    # max(-5) + 1 = -4
    assert storage.next_id(todos) == -4


def test_next_id_mixed_positive_negative_ids() -> None:
    """Mixed positive and negative IDs should return max_id + 1."""
    storage = TodoStorage()
    todos = [
        Todo(id=-10, text="negative"),
        Todo(id=5, text="positive"),
    ]
    # max(-10, 5) + 1 = 6
    assert storage.next_id(todos) == 6


def test_next_id_multiple_large_ids() -> None:
    """Multiple large IDs should return the maximum + 1."""
    storage = TodoStorage()
    todos = [
        Todo(id=1000000, text="large 1"),
        Todo(id=2000000, text="large 2"),
        Todo(id=500000, text="large 3"),
    ]
    assert storage.next_id(todos) == 2000001
