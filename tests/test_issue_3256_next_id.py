"""Tests for issue #3256: next_id returns duplicate ID.

The bug was that next_id returned 1 for empty list but also returned 1
for a non-empty list where the max ID was 0. The logic was redundant
since max(..., default=0) + 1 already handles both cases correctly.

Acceptance criteria:
- Empty list [] should return 1
- List [{id: 0}, ...] should return 1 (max=0+1)
- List [{id: 5}, ...] should return 6
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list_returns_1() -> None:
    """Empty list should return 1 as the next ID."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1, f"Expected next_id([]) to return 1, got {result}"


def test_next_id_list_with_id_0_returns_1() -> None:
    """List with only id=0 items should return 1 as the next ID."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="test")]
    result = storage.next_id(todos)
    assert result == 1, f"Expected next_id([Todo(id=0)]) to return 1, got {result}"


def test_next_id_list_with_id_5_returns_6() -> None:
    """List with max id=5 should return 6 as the next ID."""
    storage = TodoStorage()
    todos = [Todo(id=5, text="test")]
    result = storage.next_id(todos)
    assert result == 6, f"Expected next_id([Todo(id=5)]) to return 6, got {result}"


def test_next_id_list_with_multiple_items_returns_correct_next() -> None:
    """List with multiple items should return max_id + 1."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=3, text="b"), Todo(id=2, text="c")]
    result = storage.next_id(todos)
    assert result == 4, f"Expected next_id to return 4, got {result}"
