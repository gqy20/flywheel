"""Regression test for issue #3013: next_id returns negative or zero IDs.

This test ensures that next_id always returns a positive integer (>= 1),
even when existing todo IDs are negative or zero.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_negative_id_returns_positive() -> None:
    """Test that next_id returns 1 when todo has negative id.

    If the only existing todo has id=-5, next_id should return 1 (not -4).
    """
    storage = TodoStorage()
    todos = [Todo(id=-5, text="test with negative id")]

    # This should return 1, not -4
    result = storage.next_id(todos)
    assert result >= 1, f"next_id should return positive integer, got {result}"
    assert result == 1, f"Expected 1 when all IDs are negative, got {result}"


def test_next_id_with_zero_id_returns_positive() -> None:
    """Test that next_id returns 1 when todo has zero id.

    If the only existing todo has id=0, next_id should return 1.
    """
    storage = TodoStorage()
    todos = [Todo(id=0, text="test with zero id")]

    result = storage.next_id(todos)
    assert result >= 1, f"next_id should return positive integer, got {result}"
    assert result == 1, f"Expected 1 when ID is 0, got {result}"


def test_next_id_with_positive_id_returns_next() -> None:
    """Test that next_id returns max_id + 1 for positive IDs."""
    storage = TodoStorage()
    todos = [Todo(id=5, text="test")]

    result = storage.next_id(todos)
    assert result == 6, f"Expected 6 for todo with id=5, got {result}"


def test_next_id_with_empty_list_returns_one() -> None:
    """Test that next_id returns 1 for empty list."""
    storage = TodoStorage()
    todos: list[Todo] = []

    result = storage.next_id(todos)
    assert result == 1, f"Expected 1 for empty list, got {result}"


def test_next_id_with_mixed_ids_returns_next_positive() -> None:
    """Test that next_id returns max positive id + 1 for mixed IDs.

    When todos have mixed negative, zero, and positive IDs, next_id should
    return max positive ID + 1.
    """
    storage = TodoStorage()
    todos = [
        Todo(id=-10, text="negative"),
        Todo(id=0, text="zero"),
        Todo(id=5, text="positive"),
        Todo(id=-3, text="another negative"),
    ]

    result = storage.next_id(todos)
    assert result == 6, f"Expected 6 (max positive 5 + 1), got {result}"


def test_next_id_with_only_negative_ids_returns_one() -> None:
    """Test that next_id returns 1 when all IDs are negative."""
    storage = TodoStorage()
    todos = [
        Todo(id=-5, text="negative one"),
        Todo(id=-10, text="negative two"),
        Todo(id=-1, text="negative three"),
    ]

    result = storage.next_id(todos)
    assert result == 1, f"Expected 1 when all IDs are negative, got {result}"


def test_next_id_with_zero_and_negative_returns_one() -> None:
    """Test that next_id returns 1 when IDs are zero and negative."""
    storage = TodoStorage()
    todos = [
        Todo(id=0, text="zero"),
        Todo(id=-5, text="negative"),
    ]

    result = storage.next_id(todos)
    assert result == 1, f"Expected 1 for zero and negative IDs, got {result}"
