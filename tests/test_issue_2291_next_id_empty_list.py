"""Tests for issue #2291: next_id() logic bug.

The original code had redundant conditional logic:
    return (max((todo.id for todo in todos), default=0) + 1) if todos else 1

This was simplified to:
    return max((todo.id for todo in todos), default=0) + 1

The max() with default=0 already handles empty lists correctly.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_1_for_empty_list() -> None:
    """Issue #2291: next_id([]) should return 1, not 2."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1, f"Expected next_id([]) to return 1, but got {result}"


def test_next_id_returns_2_for_single_todo() -> None:
    """Issue #2291: next_id([Todo(id=1)]) should return 2."""
    storage = TodoStorage()
    result = storage.next_id([Todo(id=1, text="test")])
    assert result == 2, f"Expected next_id([Todo(id=1)]) to return 2, but got {result}"


def test_next_id_returns_max_plus_one() -> None:
    """Issue #2291: next_id() should return max_id + 1."""
    storage = TodoStorage()
    
    # Test with consecutive IDs
    result = storage.next_id([Todo(id=1, text="a"), Todo(id=2, text="b")])
    assert result == 3, f"Expected next_id([1,2]) to return 3, but got {result}"
    
    # Test with gaps in IDs
    result = storage.next_id([Todo(id=1, text="a"), Todo(id=5, text="b")])
    assert result == 6, f"Expected next_id([1,5]) to return 6, but got {result}"
