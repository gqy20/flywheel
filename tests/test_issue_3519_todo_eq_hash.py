"""Tests for Todo.__eq__ and __hash__ methods (Issue #3519).

These tests verify that:
1. Todo objects are compared based on their id field only
2. Todo objects can be hashed based on id
3. Todo objects can be used in sets and deduplicated by id
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id() -> None:
    """Two Todo objects with the same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)

    assert todo1 == todo2


def test_todo_neq_different_id() -> None:
    """Two Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task one")

    assert todo1 != todo2


def test_todo_eq_not_implemented_for_non_todo() -> None:
    """Comparing Todo with non-Todo should return NotImplemented (evaluates to False)."""
    todo = Todo(id=1, text="task")

    # Comparing with a non-Todo object should return False
    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "task"}
    assert todo is not None


def test_todo_hash_consistent() -> None:
    """hash(Todo) should return the same value for same id."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")

    assert hash(todo1) == hash(todo2)
    assert hash(todo1) == hash(1)  # hash should be based on id


def test_todo_hash_different_for_different_id() -> None:
    """hash(Todo) should return different values for different id."""
    todo1 = Todo(id=1, text="task")
    todo2 = Todo(id=2, text="task")

    assert hash(todo1) != hash(todo2)


def test_todo_set_deduplication() -> None:
    """Todo objects should deduplicate in a set based on id."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")  # Same id, different text
    todo3 = Todo(id=2, text="buy eggs")
    todo4 = Todo(id=2, text="buy juice")  # Same id as todo3, different text

    todo_set = {todo1, todo2, todo3, todo4}

    # Set should have only 2 unique todos (by id)
    assert len(todo_set) == 2


def test_todo_set_membership() -> None:
    """Todo objects should be found in set by id equivalence."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")  # Same id

    todo_set = {todo1}

    # todo2 should be considered "in" the set because it has the same id
    assert todo2 in todo_set


def test_todo_dict_key_usage() -> None:
    """Todo objects should be usable as dict keys based on id."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")  # Same id, different text

    d = {todo1: "value1"}

    # todo2 should overwrite because same id
    d[todo2] = "value2"

    assert len(d) == 1
    assert d[todo1] == "value2"
