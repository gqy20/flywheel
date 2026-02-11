"""Tests for issue #2788: next_id() edge cases.

Bug: next_id() returns different values for empty vs non-empty list with max id 0
Fix: Remove redundant ternary operator in storage.py:128
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list_returns_1() -> None:
    """Issue #2788: next_id([]) should return 1."""
    storage = TodoStorage()
    assert storage.next_id([]) == 1


def test_next_id_list_with_id_0_returns_1() -> None:
    """Issue #2788: next_id([Todo(id=0)]) should return 1."""
    storage = TodoStorage()
    todo = Todo(id=0, text="test")
    assert storage.next_id([todo]) == 1


def test_next_id_list_with_id_1_returns_2() -> None:
    """Issue #2788: next_id([Todo(id=1)]) should return 2."""
    storage = TodoStorage()
    todo = Todo(id=1, text="test")
    assert storage.next_id([todo]) == 2


def test_next_id_multiple_todos_with_0_base() -> None:
    """Issue #2788: next_id with todos having id 0 and 1 should return 2."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="zero"), Todo(id=1, text="one")]
    assert storage.next_id(todos) == 2
