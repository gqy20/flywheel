"""Tests for Todo comparison methods (Issue #6480).

These tests verify that:
1. Todo objects can be compared by id using __eq__
2. Todo objects can be sorted using __lt__
3. Todo objects can be deduplicated in sets
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_based_on_id() -> None:
    """Todo(1, 'a') == Todo(1, 'b') should return True (based on id)."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="b", done=True)

    # Same id should be equal regardless of other fields
    assert todo1 == todo2


def test_todo_inequality_different_ids() -> None:
    """Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")

    assert todo1 != todo2


def test_todo_sorting_by_id() -> None:
    """sorted([Todo(3,'c'), Todo(1,'a')]) should return list sorted by id."""
    todo3 = Todo(id=3, text="c")
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="b")

    unsorted = [todo3, todo1, todo2]
    sorted_todos = sorted(unsorted)

    assert sorted_todos[0].id == 1
    assert sorted_todos[1].id == 2
    assert sorted_todos[2].id == 3


def test_todo_set_deduplication() -> None:
    """set([Todo(1,'a'), Todo(1,'b')]) should have length 1."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    todo3 = Todo(id=2, text="c")

    unique_todos = set([todo1, todo2, todo3])

    # Only 2 unique ids (1 and 2), despite 3 todo objects
    assert len(unique_todos) == 2


def test_todo_less_than_comparison() -> None:
    """Todo comparison by id using < operator."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    assert todo1 < todo2
    assert not todo2 < todo1


def test_todo_hash_consistency() -> None:
    """Equal Todo objects should have the same hash."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    # Equal objects must have equal hashes for set/dict usage
    assert hash(todo1) == hash(todo2)
