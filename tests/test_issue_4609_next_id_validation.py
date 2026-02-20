"""Regression tests for issue #4609: next_id negative/non-contiguous ID handling.

This test suite verifies that TodoStorage.next_id() correctly handles:
1. Negative IDs - should return 1 (minimum valid positive ID)
2. Non-contiguous IDs - should return max positive ID + 1
3. Empty list - should return 1
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_negative_id_returns_1() -> None:
    """Bug #4609: next_id should return 1 when todos contain only negative IDs."""
    storage = TodoStorage()

    # When all IDs are negative, max() returns a negative number
    # next_id should still return a positive integer (1)
    todos = [Todo(id=-5, text="negative id")]
    result = storage.next_id(todos)

    assert result == 1, f"Expected 1 when all IDs are negative, got {result}"


def test_next_id_with_negative_and_positive_ids_returns_next() -> None:
    """Bug #4609: next_id should ignore negative IDs and use max positive ID + 1."""
    storage = TodoStorage()

    # Mix of negative and positive IDs
    # Should return max(positive IDs) + 1 = 11
    todos = [
        Todo(id=-5, text="negative"),
        Todo(id=10, text="positive"),
    ]
    result = storage.next_id(todos)

    assert result == 11, f"Expected 11 (max positive + 1), got {result}"


def test_next_id_with_non_contiguous_ids_returns_next() -> None:
    """Bug #4609: next_id should return max_id + 1 for non-contiguous IDs."""
    storage = TodoStorage()

    # Non-contiguous IDs (gaps)
    # Should return max + 1 = 101
    todos = [
        Todo(id=1, text="first"),
        Todo(id=100, text="hundredth"),
    ]
    result = storage.next_id(todos)

    assert result == 101, f"Expected 101 (max + 1), got {result}"


def test_next_id_with_empty_list_returns_1() -> None:
    """Baseline: next_id should return 1 for empty todo list."""
    storage = TodoStorage()

    result = storage.next_id([])

    assert result == 1, f"Expected 1 for empty list, got {result}"


def test_next_id_with_all_zero_and_negative_returns_1() -> None:
    """Bug #4609: next_id should return 1 when all IDs are zero or negative."""
    storage = TodoStorage()

    # Zero and negative IDs
    # Should return 1 since no positive IDs exist
    todos = [
        Todo(id=0, text="zero"),
        Todo(id=-1, text="minus one"),
        Todo(id=-10, text="minus ten"),
    ]
    result = storage.next_id(todos)

    assert result == 1, f"Expected 1 when no positive IDs exist, got {result}"
