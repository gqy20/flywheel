"""Tests for Todo.__eq__ and __hash__ methods (Issue #6258).

These tests verify that:
1. Todo objects can be compared by id field
2. Todo objects can be used in sets for deduplication
3. hash(Todo) works without TypeError
4. Same id returns same hash value
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_based_on_id() -> None:
    """Todo.__eq__ should compare based on id field."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)

    # Same id, different text/done - should be equal
    assert todo1 == todo2


def test_todo_neq_different_id() -> None:
    """Todo.__eq__ should return False for different ids."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    # Same text/done, different id - should not be equal
    assert todo1 != todo2


def test_todo_hash_no_error() -> None:
    """hash(Todo) should not raise TypeError."""
    todo = Todo(id=1, text="buy milk", done=False)

    # Should not raise TypeError
    hash_value = hash(todo)
    assert isinstance(hash_value, int)


def test_todo_hash_consistent_for_same_id() -> None:
    """hash(Todo) should return same value for same id."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)

    # Same id should have same hash
    assert hash(todo1) == hash(todo2)


def test_todo_set_deduplication() -> None:
    """Todo objects with same id should be deduplicated in a set."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)
    todo3 = Todo(id=2, text="buy eggs", done=False)

    todo_set = {todo1, todo2, todo3}

    # Should have only 2 items (todo1 and todo2 are same id)
    assert len(todo_set) == 2


def test_todo_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)

    todo_dict = {todo1: "first"}

    # todo2 should map to same key as todo1
    assert todo_dict[todo2] == "first"


def test_todo_eq_with_non_todo() -> None:
    """Todo.__eq__ should return NotImplemented for non-Todo types."""
    todo = Todo(id=1, text="buy milk", done=False)

    # Comparing with non-Todo should return NotImplemented (evaluates to False)
    assert todo != 1
    assert todo != "todo"
    assert todo != {"id": 1, "text": "buy milk"}
