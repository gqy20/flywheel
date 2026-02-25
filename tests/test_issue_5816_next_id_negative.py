"""Tests for issue #5816: TodoStorage.next_id returns negative values when only negative IDs exist.

Bug: TodoStorage.next_id returns negative values when only negative IDs exist in storage,
potentially causing ID conflicts or unexpected behavior.

Fix: next_id should always return a positive integer (minimum 1) by filtering for positive IDs
before computing the max.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list_returns_1() -> None:
    """next_id([]) should return 1."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1


def test_next_id_only_negative_ids_returns_1() -> None:
    """next_id([Todo(id=-5), Todo(id=-10)]) should return 1, not -4."""
    storage = TodoStorage()
    todos = [Todo(id=-5, text="negative 5"), Todo(id=-10, text="negative 10")]
    result = storage.next_id(todos)
    assert result == 1, f"Expected 1, got {result}"


def test_next_id_mixed_positive_negative_returns_max_positive_plus_1() -> None:
    """next_id([Todo(id=5), Todo(id=-10)]) should return 6."""
    storage = TodoStorage()
    todos = [Todo(id=5, text="positive 5"), Todo(id=-10, text="negative 10")]
    result = storage.next_id(todos)
    assert result == 6, f"Expected 6, got {result}"


def test_next_id_with_zero_id_returns_2() -> None:
    """next_id([Todo(id=0), Todo(id=1)]) should return 2 (0 is not positive)."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="zero"), Todo(id=1, text="one")]
    result = storage.next_id(todos)
    assert result == 2, f"Expected 2, got {result}"


def test_next_id_all_zero_and_negative_returns_1() -> None:
    """next_id([Todo(id=0), Todo(id=-1)]) should return 1."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="zero"), Todo(id=-1, text="negative one")]
    result = storage.next_id(todos)
    assert result == 1, f"Expected 1, got {result}"
