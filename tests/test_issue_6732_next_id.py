"""Tests for next_id with non-contiguous IDs.

Regression test for issue #6732: next_id should return the smallest unused
positive integer ID, not just max(existing_ids) + 1.

This ensures that after removing a todo, new todos can reuse the freed ID.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_1_for_empty_list() -> None:
    """Test that next_id returns 1 when there are no todos."""
    storage = TodoStorage()
    todos: list[Todo] = []
    assert storage.next_id(todos) == 1


def test_next_id_returns_4_for_contiguous_ids_1_2_3() -> None:
    """Test that next_id returns 4 when IDs are [1, 2, 3]."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]
    assert storage.next_id(todos) == 4


def test_next_id_fills_gap_in_non_contiguous_ids() -> None:
    """Test that next_id returns the smallest unused ID when there are gaps.

    This is the core bug fix for issue #6732:
    If todos have IDs [1, 5], next_id should return 2 (not 6).
    """
    storage = TodoStorage()
    # IDs 1 and 5 exist, but 2, 3, 4 are available
    todos = [Todo(id=1, text="first"), Todo(id=5, text="fifth")]
    assert storage.next_id(todos) == 2


def test_next_id_fills_multiple_gaps() -> None:
    """Test that next_id fills gaps in order from smallest to largest."""
    storage = TodoStorage()
    # Only ID 5 exists, so 1 should be returned
    todos = [Todo(id=5, text="fifth")]
    assert storage.next_id(todos) == 1


def test_next_id_fills_second_gap_after_first_is_used() -> None:
    """Test that next_id returns 3 when IDs are [1, 2, 5]."""
    storage = TodoStorage()
    # IDs 1, 2, 5 exist, so 3 should be returned (the first gap)
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=5, text="fifth"),
    ]
    assert storage.next_id(todos) == 3


def test_next_id_handles_large_gaps() -> None:
    """Test that next_id handles large ID gaps correctly."""
    storage = TodoStorage()
    # Only ID 100 exists, so 1 should be returned
    todos = [Todo(id=100, text="hundred")]
    assert storage.next_id(todos) == 1


def test_next_id_preserves_sequential_behavior() -> None:
    """Test that normal sequential ID assignment still works.

    This ensures backward compatibility: when IDs are [1, 2, 3],
    next_id should still return 4.
    """
    storage = TodoStorage()
    todos = [Todo(id=i, text=f"todo-{i}") for i in range(1, 100)]
    assert storage.next_id(todos) == 100
