"""Tests for issue #5584: next_id() simplification.

This module tests that next_id() correctly handles:
1. Empty list - should return 1
2. Non-contiguous IDs after deletions - should return max_id + 1
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_1_for_empty_list() -> None:
    """Issue #5584: next_id([]) should return 1."""
    storage = TodoStorage()
    assert storage.next_id([]) == 1


def test_next_id_returns_max_plus_1_for_non_contiguous_ids() -> None:
    """Issue #5584: next_id([Todo(id=10)]) should return 11."""
    storage = TodoStorage()
    todos = [Todo(id=10, text="test")]
    assert storage.next_id(todos) == 11


def test_next_id_handles_mixed_non_contiguous_ids() -> None:
    """Issue #5584: next_id should return max_id + 1 regardless of gaps."""
    storage = TodoStorage()
    # Simulate IDs after deletions: [1, 3, 5, 10]
    todos = [
        Todo(id=1, text="first"),
        Todo(id=3, text="third"),
        Todo(id=5, text="fifth"),
        Todo(id=10, text="tenth"),
    ]
    assert storage.next_id(todos) == 11


def test_next_id_returns_2_for_single_todo_with_id_1() -> None:
    """Issue #5584: Verify basic case still works."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="only todo")]
    assert storage.next_id(todos) == 2
