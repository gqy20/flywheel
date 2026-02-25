"""Regression tests for issue #5734: next_id() redundant conditional.

The next_id() function had redundant logic:
    return (max((todo.id for todo in todos), default=0) + 1) if todos else 1

The 'if todos else 1' conditional is unnecessary because:
- max() with default=0 handles empty generator correctly
- For empty list: max([], default=0) returns 0, then 0+1=1
- For non-empty list: the max() already provides correct result

This test verifies that simplifying to:
    return max((todo.id for todo in todos), default=0) + 1

produces correct behavior in all cases.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_1_for_empty_list() -> None:
    """next_id() should return 1 for an empty todo list."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1, f"Expected next_id([]) to return 1, got {result}"


def test_next_id_returns_next_id_after_highest() -> None:
    """next_id() should return max_id + 1 for non-empty list."""
    storage = TodoStorage()
    todos = [Todo(id=5, text="test")]
    result = storage.next_id(todos)
    assert result == 6, f"Expected next_id([Todo(id=5)]) to return 6, got {result}"


def test_next_id_handles_single_item_with_id_zero() -> None:
    """next_id() should handle list with id=0 item correctly.

    This is the key edge case: if a list has only items with id=0,
    max() returns 0, so next_id should return 1.

    This should NOT collide with empty list case - both return 1,
    but for semantically correct reasons (empty list has no IDs,
    list with id=0 has highest ID of 0).
    """
    storage = TodoStorage()
    todos = [Todo(id=0, text="zero id item")]
    result = storage.next_id(todos)
    assert result == 1, f"Expected next_id([Todo(id=0)]) to return 1, got {result}"


def test_next_id_handles_mixed_ids() -> None:
    """next_id() should find max ID among mixed IDs."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="zero"), Todo(id=5, text="five"), Todo(id=3, text="three")]
    result = storage.next_id(todos)
    assert result == 6, f"Expected next_id to return 6 (max was 5), got {result}"


def test_next_id_handles_consecutive_ids() -> None:
    """next_id() should work with consecutive IDs starting from 1."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first"), Todo(id=2, text="second"), Todo(id=3, text="third")]
    result = storage.next_id(todos)
    assert result == 4, f"Expected next_id to return 4, got {result}"
