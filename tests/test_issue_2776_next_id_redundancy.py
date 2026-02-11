"""Test for issue #2776: next_id() logic is redundant and potentially incorrect for edge cases.

The issue is that the current implementation:
    return (max((todo.id for todo in todos), default=0) + 1) if todos else 1

Has redundant logic - the 'if todos else 1' branch is unnecessary because
max(..., default=0) already returns 0 for empty sequences, and 0 + 1 = 1.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list() -> None:
    """Test that next_id returns 1 for an empty todos list."""
    storage = TodoStorage()
    assert storage.next_id([]) == 1


def test_next_id_single_todo() -> None:
    """Test that next_id returns 2 for a list with a single todo with id=1."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="x")]
    assert storage.next_id(todos) == 2


def test_next_id_with_gaps() -> None:
    """Test that next_id handles gaps in IDs correctly."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="x"), Todo(id=5, text="y")]
    assert storage.next_id(todos) == 6


def test_next_id_with_consecutive_ids() -> None:
    """Test that next_id returns max + 1 for consecutive IDs."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="x"), Todo(id=2, text="y")]
    assert storage.next_id(todos) == 3


def test_next_id_with_large_id() -> None:
    """Test that next_id handles large ID values correctly."""
    storage = TodoStorage()
    todos = [Todo(id=1000, text="large id")]
    assert storage.next_id(todos) == 1001
