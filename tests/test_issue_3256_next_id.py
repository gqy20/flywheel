"""Regression test for issue #3256: next_id redundant conditional logic.

The next_id function had redundant logic:
  return (max((todo.id for todo in todos), default=0) + 1) if todos else 1

The 'if todos else 1' conditional is unnecessary because max(..., default=0)
already handles the empty list case correctly, returning 0 which then becomes 1.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list_returns_1() -> None:
    """Empty list should return 1 as the first ID."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1


def test_next_id_list_with_id_0_returns_1() -> None:
    """List containing only id=0 should return 1 (max=0, +1=1)."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="test")]
    result = storage.next_id(todos)
    assert result == 1


def test_next_id_list_with_id_5_returns_6() -> None:
    """List with max id=5 should return 6."""
    storage = TodoStorage()
    todos = [Todo(id=5, text="test")]
    result = storage.next_id(todos)
    assert result == 6


def test_next_id_multiple_todos_returns_max_plus_1() -> None:
    """List with multiple todos should return max(id) + 1."""
    storage = TodoStorage()
    todos = [
        Todo(id=1, text="first"),
        Todo(id=5, text="second"),
        Todo(id=3, text="third"),
    ]
    result = storage.next_id(todos)
    assert result == 6  # max(1, 5, 3) + 1 = 6


def test_next_id_negative_ids_handled_correctly() -> None:
    """Edge case: negative IDs should be handled by max() correctly."""
    storage = TodoStorage()
    # This is an edge case - if somehow a negative ID got in
    todos = [Todo(id=-1, text="negative")]
    result = storage.next_id(todos)
    assert result == 0  # max(-1) + 1 = 0
