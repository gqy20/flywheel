"""Tests for issue #5069: next_id should handle gaps in todo IDs.

Bug: next_id returns incorrect ID when todo IDs are non-contiguous or have gaps.
Location: src/flywheel/storage.py:128

The original implementation used max(todo.id) + 1, which produces duplicate IDs
when the highest-ID todo is deleted. The fix finds the smallest unused positive
integer ID.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_1_for_empty_list() -> None:
    """next_id should return 1 when there are no todos."""
    storage = TodoStorage()
    assert storage.next_id([]) == 1


def test_next_id_returns_max_plus_1_for_contiguous_ids() -> None:
    """next_id should return max+1 when IDs are contiguous (no gaps)."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]
    assert storage.next_id(todos) == 4


def test_next_id_fills_gap_at_lowest_position() -> None:
    """next_id should return 2 when there's a gap at position 2 (IDs: 1, 3)."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=3, text="c")]
    assert storage.next_id(todos) == 2


def test_next_id_fills_gap_at_position_1() -> None:
    """next_id should return 1 when ID 1 is missing (IDs: 2, 3)."""
    storage = TodoStorage()
    todos = [Todo(id=2, text="b"), Todo(id=3, text="c")]
    assert storage.next_id(todos) == 1


def test_next_id_fills_multiple_gaps_at_lowest() -> None:
    """next_id should return 3 when IDs are 1, 2, 5 (gap at 3)."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=5, text="e")]
    assert storage.next_id(todos) == 3


def test_next_id_handles_single_todo() -> None:
    """next_id should return 2 when there's only one todo with ID 1."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="a")]
    assert storage.next_id(todos) == 2


def test_next_id_handles_single_todo_with_non_one_id() -> None:
    """next_id should return 1 when the only todo has a non-1 ID."""
    storage = TodoStorage()
    todos = [Todo(id=5, text="e")]
    assert storage.next_id(todos) == 1


def test_next_id_no_duplicate_after_delete_scenario() -> None:
    """
    Regression test for the original bug scenario:
    1. Create todos with IDs 1, 2, 3
    2. Delete todo with ID 3
    3. next_id should return 3 (the freed slot)
    4. Create new todo, delete it again
    5. next_id should still return 3 (not 4)
    """
    storage = TodoStorage()
    # Simulate: created todos 1, 2, 3, then deleted todo 3
    todos = [Todo(id=1, text="a"), Todo(id=2, text="b")]
    assert storage.next_id(todos) == 3
