"""Tests for Todo __eq__ and __hash__ methods (Issue #3045).

These tests verify that Todo objects can be compared by id and used in sets
or as dictionary keys.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_based_on_id() -> None:
    """Todos with the same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    assert todo1 == todo2


def test_todo_eq_different_ids() -> None:
    """Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    assert todo1 != todo2


def test_todo_eq_with_done_flag() -> None:
    """Todo equality should ignore done flag, only compare id."""
    todo1 = Todo(id=1, text="task", done=False)
    todo2 = Todo(id=1, text="task", done=True)
    assert todo1 == todo2


def test_hash_does_not_raise() -> None:
    """Todo objects should be hashable."""
    todo = Todo(id=1, text="a")
    # This should not raise TypeError
    hash(todo)


def test_hash_based_on_id() -> None:
    """Todos with the same id should have the same hash."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    assert hash(todo1) == hash(todo2)


def test_hash_different_for_different_ids() -> None:
    """Todos with different ids should have different hashes."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    # Hash collisions are theoretically possible but unlikely for small integers
    assert hash(todo1) != hash(todo2)


def test_todo_in_set() -> None:
    """Todo objects should be usable in a set."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")  # Same id as todo1
    todo3 = Todo(id=2, text="c")

    todo_set = {todo1, todo2, todo3}
    # Set should deduplicate by id, so only 2 items
    assert len(todo_set) == 2


def test_todo_as_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")  # Same id as todo1

    d = {todo1: "value1"}
    # todo2 has same id, so should access the same key
    assert d[todo2] == "value1"
