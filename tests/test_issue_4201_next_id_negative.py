"""Regression test for issue #4201: next_id() returns 0 when all IDs are negative.

This test suite verifies that next_id() always returns a positive integer (>=1)
even when all existing todo IDs are negative numbers.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list_returns_1() -> None:
    """Test that next_id returns 1 for an empty todo list."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1, f"Expected 1 for empty list, got {result}"


def test_next_id_with_negative_ids_returns_positive() -> None:
    """Test that next_id returns a positive integer when all IDs are negative.

    This is the core regression test for issue #4201.
    When todos have negative IDs like -5 and -3, the old implementation
    would return max(-5, -3) + 1 = -2, which is invalid.
    The fix ensures we always return a positive integer (>=1).
    """
    storage = TodoStorage()
    todos = [
        Todo(id=-5, text="negative id todo 1"),
        Todo(id=-3, text="negative id todo 2"),
    ]
    result = storage.next_id(todos)
    assert result >= 1, f"Expected positive integer (>=1), got {result}"


def test_next_id_with_single_negative_id_returns_positive() -> None:
    """Test that next_id returns 1 when the only ID is -1."""
    storage = TodoStorage()
    todos = [Todo(id=-1, text="negative id todo")]
    result = storage.next_id(todos)
    assert result >= 1, f"Expected positive integer (>=1), got {result}"


def test_next_id_with_large_negative_id_returns_positive() -> None:
    """Test that next_id returns positive even with very large negative IDs."""
    storage = TodoStorage()
    todos = [Todo(id=-999999, text="large negative id todo")]
    result = storage.next_id(todos)
    assert result >= 1, f"Expected positive integer (>=1), got {result}"


def test_next_id_with_mixed_positive_and_negative_ids() -> None:
    """Test that next_id works correctly with mixed positive and negative IDs."""
    storage = TodoStorage()
    todos = [
        Todo(id=-10, text="negative"),
        Todo(id=5, text="positive"),
        Todo(id=-2, text="another negative"),
    ]
    result = storage.next_id(todos)
    # Should return max(5) + 1 = 6, not based on negative IDs
    assert result == 6, f"Expected 6, got {result}"


def test_next_id_always_returns_at_least_1() -> None:
    """Test that next_id never returns 0 or negative values."""
    storage = TodoStorage()

    # Test various edge cases
    test_cases = [
        [],  # empty list
        [Todo(id=-1, text="test")],  # single negative
        [Todo(id=-2, text="test")],  # -2 + 1 = -1 (old behavior)
        [Todo(id=-5, text="test")],  # -5 + 1 = -4 (old behavior)
    ]

    for todos in test_cases:
        result = storage.next_id(todos)
        assert result >= 1, f"next_id({todos}) returned {result}, expected >= 1"
