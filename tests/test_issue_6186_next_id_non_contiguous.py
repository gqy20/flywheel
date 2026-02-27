"""Tests for issue #6186: next_id() should return lowest unused ID.

Regression test for bug where next_id() returned max+1 instead of
the lowest unused ID when todos have non-contiguous IDs (e.g., after deletion).
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_lowest_unused_with_non_contiguous_ids():
    """Given todos with IDs [1, 3, 5], next_id() should return 2 (lowest unused)."""
    storage = TodoStorage()
    todos = [
        Todo(id=1, text="task 1"),
        Todo(id=3, text="task 3"),
        Todo(id=5, text="task 5"),
    ]

    result = storage.next_id(todos)

    assert result == 2, f"Expected 2 (lowest unused), got {result}"


def test_next_id_returns_4_with_contiguous_ids():
    """Given todos with IDs [1, 2, 3], next_id() should return 4."""
    storage = TodoStorage()
    todos = [
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2"),
        Todo(id=3, text="task 3"),
    ]

    result = storage.next_id(todos)

    assert result == 4, f"Expected 4, got {result}"


def test_next_id_returns_1_with_empty_list():
    """Given an empty todo list, next_id() should return 1."""
    storage = TodoStorage()
    todos = []

    result = storage.next_id(todos)

    assert result == 1, f"Expected 1, got {result}"


def test_next_id_handles_gap_at_start():
    """Given todos with IDs [2, 3, 4], next_id() should return 1."""
    storage = TodoStorage()
    todos = [
        Todo(id=2, text="task 2"),
        Todo(id=3, text="task 3"),
        Todo(id=4, text="task 4"),
    ]

    result = storage.next_id(todos)

    assert result == 1, f"Expected 1 (lowest unused), got {result}"


def test_next_id_handles_multiple_gaps():
    """Given todos with IDs [1, 4, 7], next_id() should return 2."""
    storage = TodoStorage()
    todos = [
        Todo(id=1, text="task 1"),
        Todo(id=4, text="task 4"),
        Todo(id=7, text="task 7"),
    ]

    result = storage.next_id(todos)

    assert result == 2, f"Expected 2 (lowest unused), got {result}"
