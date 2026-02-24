"""Regression tests for issue #5530: next_id() simplification.

Bug: next_id() has redundant conditional logic 'if todos else 1' that is
unnecessary because max() with default=0 on an empty generator returns 0,
and 0+1=1, which is the correct result for an empty list.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list_returns_1() -> None:
    """Verify next_id([]) returns 1 for empty list."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1, f"Expected 1 for empty list, got {result}"


def test_next_id_single_todo_returns_next() -> None:
    """Verify next_id([Todo(id=5)]) returns 6."""
    storage = TodoStorage()
    todos = [Todo(id=5, text="test")]
    result = storage.next_id(todos)
    assert result == 6, f"Expected 6 for single todo with id=5, got {result}"


def test_next_id_multiple_todos_returns_max_plus_one() -> None:
    """Verify next_id returns max(id) + 1 for multiple todos."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=3, text="c")]
    result = storage.next_id(todos)
    assert result == 6, f"Expected 6 for todos with max id=5, got {result}"


def test_next_id_with_id_zero() -> None:
    """Verify next_id works correctly when a todo has id=0."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="zero")]
    result = storage.next_id(todos)
    assert result == 1, f"Expected 1 for todo with id=0, got {result}"


def test_next_id_sequential_ids() -> None:
    """Verify next_id works with sequential ids starting from 1."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first"), Todo(id=2, text="second"), Todo(id=3, text="third")]
    result = storage.next_id(todos)
    assert result == 4, f"Expected 4 for sequential ids 1-3, got {result}"
