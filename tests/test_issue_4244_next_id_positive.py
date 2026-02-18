"""Regression tests for issue #4244: next_id() must always return positive ID.

This test suite verifies that TodoStorage.next_id() always returns a positive
integer (>= 1), even when the existing todos have negative or zero IDs.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_negative_ids_returns_1() -> None:
    """When all todos have negative IDs, next_id() should return 1."""
    storage = TodoStorage()
    todos = [Todo(id=-5, text="negative one"), Todo(id=-3, text="negative two")]
    result = storage.next_id(todos)
    assert result == 1, f"Expected 1 for next_id with all negative IDs, got {result}"


def test_next_id_with_zero_id_returns_1() -> None:
    """When max ID is 0, next_id() should return 1 (not 0)."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="zero id")]
    result = storage.next_id(todos)
    assert result == 1, f"Expected 1 for next_id when max ID is 0, got {result}"


def test_next_id_with_positive_ids_returns_next() -> None:
    """When todos have positive IDs, next_id() should return max + 1."""
    storage = TodoStorage()
    todos = [Todo(id=3, text="positive")]
    result = storage.next_id(todos)
    assert result == 4, f"Expected 4 for next_id when max ID is 3, got {result}"


def test_next_id_with_empty_list_returns_1() -> None:
    """When todos list is empty, next_id() should return 1."""
    storage = TodoStorage()
    todos: list[Todo] = []
    result = storage.next_id(todos)
    assert result == 1, f"Expected 1 for next_id with empty list, got {result}"


def test_next_id_with_mixed_negative_and_positive_returns_next_positive() -> None:
    """When todos have mixed IDs, next_id() should return max + 1 (or 1 if that's negative)."""
    storage = TodoStorage()
    # Mix of negative and positive IDs
    todos = [Todo(id=-5, text="negative"), Todo(id=3, text="positive")]
    result = storage.next_id(todos)
    assert result == 4, f"Expected 4 for next_id with max ID 3, got {result}"


def test_next_id_never_returns_zero_or_negative() -> None:
    """next_id() should never return 0 or a negative number."""
    storage = TodoStorage()

    # Test various edge cases
    test_cases = [
        ([Todo(id=-1, text="a"), Todo(id=-10, text="b")], 1),  # All negative
        ([Todo(id=0, text="zero")], 1),  # Zero ID
        ([Todo(id=-1, text="a")], 1),  # Single negative
        ([], 1),  # Empty list
        ([Todo(id=1, text="a")], 2),  # Positive starting at 1
        ([Todo(id=100, text="a")], 101),  # Large positive
    ]

    for todos, expected in test_cases:
        result = storage.next_id(todos)
        assert result >= 1, f"next_id returned {result} for case {todos}, expected >= 1"
        assert result == expected, f"Expected {expected}, got {result} for case {todos}"
