"""Tests for issue #4201: next_id() should always return positive integer.

Bug: next_id() method returns 0 when all IDs are negative, which can cause
logic problems since todo IDs should be positive integers (>=1).

Fix: Ensure next_id always returns a positive integer by using max(1, ...)
wrapper or similar logic.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list_returns_1() -> None:
    """next_id([]) should return 1."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1


def test_next_id_with_negative_ids_returns_positive() -> None:
    """next_id should return positive integer even when all IDs are negative.

    This is the main regression test for issue #4201.
    When all todo IDs are negative (e.g., corrupted data), next_id should
    still return a valid positive ID (>=1).
    """
    storage = TodoStorage()
    # Simulate corrupted data with negative IDs
    todos = [Todo(id=-5, text="negative one"), Todo(id=-3, text="negative two")]

    result = storage.next_id(todos)
    # The result should be a positive integer >= 1
    assert result >= 1, f"next_id should return >= 1, got {result}"


def test_next_id_with_all_negative_ids_never_returns_zero() -> None:
    """Ensure next_id never returns 0 when IDs are negative.

    Specific edge case: if max ID is -1, then -1 + 1 = 0, which is invalid.
    """
    storage = TodoStorage()
    # Test case where max negative ID is -1 (would result in 0 with buggy code)
    todos = [Todo(id=-1, text="edge case")]

    result = storage.next_id(todos)
    assert result >= 1, f"next_id should never return 0, got {result}"


def test_next_id_with_mixed_ids_returns_correct_next() -> None:
    """next_id should work correctly with mixed positive and negative IDs."""
    storage = TodoStorage()
    # Mix of positive and negative IDs - should find max positive and add 1
    todos = [
        Todo(id=-5, text="negative"),
        Todo(id=3, text="positive one"),
        Todo(id=7, text="positive two"),
    ]

    result = storage.next_id(todos)
    assert result == 8, f"next_id should return 8 (max positive + 1), got {result}"


def test_next_id_preserves_existing_behavior() -> None:
    """Ensure the fix doesn't break normal positive ID behavior."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]

    result = storage.next_id(todos)
    assert result == 3
