"""Tests for issue #3013: next_id returns negative or zero IDs with negative existing IDs."""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_negative_todo_id_returns_positive_one() -> None:
    """Bug #3013: next_id should return 1 when all existing IDs are negative."""
    storage = TodoStorage()

    # When all todos have negative IDs, next_id should return 1, not -4
    todos = [Todo(id=-5, text="negative id todo")]
    assert storage.next_id(todos) == 1, "Expected 1 when all existing IDs are negative"


def test_next_id_with_zero_todo_id_returns_positive_one() -> None:
    """Bug #3013: next_id should return 1 when max existing ID is 0."""
    storage = TodoStorage()

    # When max ID is 0, next_id should return 1
    todos = [Todo(id=0, text="zero id todo")]
    assert storage.next_id(todos) == 1, "Expected 1 when max existing ID is 0"


def test_next_id_with_positive_todo_id_returns_incremented() -> None:
    """Verify normal behavior: next_id should return max_id + 1 for positive IDs."""
    storage = TodoStorage()

    # Normal case: max ID is positive, should return max + 1
    todos = [Todo(id=5, text="positive id todo")]
    assert storage.next_id(todos) == 6, "Expected max_id + 1 for positive IDs"


def test_next_id_with_empty_list_returns_one() -> None:
    """Verify empty list returns 1."""
    storage = TodoStorage()

    # Empty list should return 1
    assert storage.next_id([]) == 1, "Expected 1 for empty todo list"


def test_next_id_with_mixed_including_negative_returns_max_plus_one() -> None:
    """Bug #3013: Mixed IDs with negatives should use max positive ID + 1."""
    storage = TodoStorage()

    # Mixed: negative and positive IDs - should use max positive + 1
    todos = [
        Todo(id=-5, text="negative id"),
        Todo(id=10, text="positive id"),
    ]
    assert storage.next_id(todos) == 11, "Expected max positive ID + 1 for mixed IDs"
