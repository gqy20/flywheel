"""Tests for issue #2374 - next_id() consistency.

Bug: next_id() returns inconsistent value for empty todos list
Location: src/flywheel/storage.py:128

The issue is that the conditional `if todos else 1` is redundant because
`max(..., default=0) + 1` already handles the empty list case correctly.

These tests verify the expected behavior of next_id() for various inputs.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_empty_list_returns_1() -> None:
    """next_id([]) should return 1 for an empty list."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1, f"Expected 1, got {result}"


def test_next_id_with_consecutive_ids_returns_max_plus_1() -> None:
    """next_id([Todo(id=1), Todo(id=2)]) should return 3."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
    result = storage.next_id(todos)
    assert result == 3, f"Expected 3, got {result}"


def test_next_id_with_non_consecutive_ids_returns_max_plus_1() -> None:
    """next_id([Todo(id=5)]) should return 6."""
    storage = TodoStorage()
    todos = [Todo(id=5, text="skip")]
    result = storage.next_id(todos)
    assert result == 6, f"Expected 6, got {result}"


def test_next_id_with_single_todo_returns_2() -> None:
    """next_id([Todo(id=1)]) should return 2."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="only")]
    result = storage.next_id(todos)
    assert result == 2, f"Expected 2, got {result}"


def test_next_id_with_gap_in_ids_returns_max_plus_1() -> None:
    """next_id([Todo(id=1), Todo(id=5)]) should return 6."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first"), Todo(id=5, text="fifth")]
    result = storage.next_id(todos)
    assert result == 6, f"Expected 6, got {result}"
