"""Dedicated unit tests for TodoStorage.next_id() method."""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list_returns_1() -> None:
    """Empty list should return 1 as the first ID."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1


def test_next_id_single_element_returns_next() -> None:
    """Single todo element should return max(id) + 1."""
    storage = TodoStorage()
    todos = [Todo(id=5, text="single")]
    result = storage.next_id(todos)
    assert result == 6


def test_next_id_non_sequential_ids() -> None:
    """Non-sequential IDs should return max(id) + 1."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first"), Todo(id=100, text="second")]
    result = storage.next_id(todos)
    assert result == 101


def test_next_id_sequential_ids() -> None:
    """Sequential IDs should return max(id) + 1."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]
    result = storage.next_id(todos)
    assert result == 4


def test_next_id_negative_ids() -> None:
    """Negative IDs should return max(id) + 1 (which could be 0 or negative)."""
    storage = TodoStorage()
    todos = [Todo(id=-5, text="negative")]
    result = storage.next_id(todos)
    assert result == -4


def test_next_id_large_id() -> None:
    """Very large IDs should be handled correctly."""
    storage = TodoStorage()
    todos = [Todo(id=999999999, text="large")]
    result = storage.next_id(todos)
    assert result == 1000000000
