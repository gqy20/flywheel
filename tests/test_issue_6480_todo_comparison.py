"""Tests for Todo comparison methods (__eq__ and __lt__).

Issue #6480: Add comparison methods to support sorting and deduplication.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_based_on_id() -> None:
    """Todo(1, 'a') == Todo(1, 'b') should return True (same id)."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    # Same id means equal, regardless of other fields
    assert todo1 == todo2


def test_todo_inequality_different_id() -> None:
    """Todo(1, 'a') != Todo(2, 'a') should return True (different id)."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")

    assert todo1 != todo2


def test_todo_sorting_by_id() -> None:
    """sorted([Todo(3,'c'), Todo(1,'a')]) should return list sorted by id."""
    todo3 = Todo(id=3, text="c")
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="b")

    unsorted_list = [todo3, todo1, todo2]
    sorted_list = sorted(unsorted_list)

    assert sorted_list[0].id == 1
    assert sorted_list[1].id == 2
    assert sorted_list[2].id == 3


def test_todo_set_deduplication() -> None:
    """set([Todo(1,'a'), Todo(1,'b')]) should have length 1 (same id)."""
    todo1a = Todo(id=1, text="a")
    todo1b = Todo(id=1, text="b")

    # Both have same id, so set should deduplicate to 1 item
    todo_set = {todo1a, todo1b}
    assert len(todo_set) == 1


def test_todo_less_than_comparison() -> None:
    """Todo(1, 'a') < Todo(2, 'b') should return True."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="b")

    assert todo1 < todo2
    assert not todo2 < todo1


def test_todo_greater_than_comparison() -> None:
    """Todo(2, 'b') > Todo(1, 'a') should return True."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="b")

    assert todo2 > todo1
    assert not todo1 > todo2


def test_todo_comparison_with_done_flag() -> None:
    """Comparison should be based on id only, not done status."""
    todo1_done = Todo(id=1, text="a", done=True)
    todo1_undone = Todo(id=1, text="b", done=False)

    # Same id means equal, even with different done status
    assert todo1_done == todo1_undone
