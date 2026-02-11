"""Regression test for Issue #2827 - redundant conditional in next_id()."""

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list_returns_1() -> None:
    """Issue #2827: Empty list should return 1 (first todo ID)."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1, f"Expected 1 for empty list, got {result}"


def test_next_id_single_todo_returns_2() -> None:
    """Issue #2827: Single todo with id=1 should return 2."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first")]
    result = storage.next_id(todos)
    assert result == 2, f"Expected 2 for [id=1], got {result}"


def test_next_id_multiple_todos_returns_max_plus_one() -> None:
    """Issue #2827: Non-sequential IDs should return max + 1."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first"), Todo(id=5, text="fifth")]
    result = storage.next_id(todos)
    assert result == 6, f"Expected 6 for [id=1, id=5], got {result}"
