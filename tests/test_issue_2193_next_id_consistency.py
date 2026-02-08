"""Regression test for issue #2193: next_id() produces inconsistent results.

This test verifies that next_id() correctly handles both empty and non-empty lists
consistently. The original implementation had a redundant 'if todos else 1' clause
that produced the same result but was unnecessarily complex.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_empty_list() -> None:
    """Issue #2193: next_id([]) should return 1 for first todo."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1, f"Expected next_id([]) to return 1, got {result}"


def test_next_id_with_single_todo() -> None:
    """Issue #2193: next_id([Todo(id=1)]) should return 2."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first")]
    result = storage.next_id(todos)
    assert result == 2, f"Expected next_id([Todo(id=1)]) to return 2, got {result}"


def test_next_id_with_multiple_todos() -> None:
    """Issue #2193: next_id() should return max_id + 1."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
    result = storage.next_id(todos)
    assert result == 3, f"Expected next_id([Todo(id=1), Todo(id=2)]) to return 3, got {result}"


def test_next_id_with_gap_in_ids() -> None:
    """Issue #2193: next_id() should return max_id + 1 even with gaps."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first"), Todo(id=5, text="fifth")]
    result = storage.next_id(todos)
    assert result == 6, f"Expected next_id([Todo(id=1), Todo(id=5)]) to return 6, got {result}"


def test_next_id_consistency_with_empty_and_nonempty() -> None:
    """Issue #2193: Verify empty and non-empty cases work identically."""
    storage = TodoStorage()

    # Empty case should return 1
    empty_result = storage.next_id([])

    # Non-empty case with id=0 equivalent (default=0 case)
    # Since max(..., default=0) + 1 should give same result
    nonempty_result = storage.next_id([Todo(id=1, text="test")])

    # Verify the logic is consistent
    assert empty_result == 1, f"Empty list should return 1, got {empty_result}"
    assert nonempty_result == 2, f"Single todo (id=1) should return 2, got {nonempty_result}"
