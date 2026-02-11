"""Tests for Issue #2776: next_id() logic simplification.

This test file ensures that the simplified next_id() logic produces
correct results for all edge cases.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list_returns_1() -> None:
    """Bug #2776: Empty todos list should return 1 as next ID."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1, f"Expected 1 for empty list, got {result}"


def test_next_id_single_todo_returns_next() -> None:
    """Bug #2776: Single todo with id=1 should return 2."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="x")]
    result = storage.next_id(todos)
    assert result == 2, f"Expected 2 for [Todo(1)], got {result}"


def test_next_id_with_gaps_returns_max_plus_one() -> None:
    """Bug #2776: Todos with gaps should return max(id) + 1."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="x"), Todo(id=5, text="y")]
    result = storage.next_id(todos)
    assert result == 6, f"Expected 6 for [Todo(1), Todo(5)], got {result}"


def test_next_id_multiple_consecutive_returns_next() -> None:
    """Bug #2776: Multiple consecutive todos should return max + 1."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]
    result = storage.next_id(todos)
    assert result == 4, f"Expected 4 for [Todo(1), Todo(2), Todo(3)], got {result}"


def test_next_id_large_ids_works_correctly() -> None:
    """Bug #2776: Large ID values should work correctly."""
    storage = TodoStorage()
    todos = [Todo(id=1000, text="large")]
    result = storage.next_id(todos)
    assert result == 1001, f"Expected 1001 for [Todo(1000)], got {result}"
