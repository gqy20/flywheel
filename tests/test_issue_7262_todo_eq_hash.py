"""Tests for Todo.__eq__ and __hash__ methods (Issue #7262).

These tests verify that:
1. Todo objects compare equal by id (not by all fields)
2. Todo objects can be hashed by id
3. Todo objects can be used in sets and as dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_by_id() -> None:
    """Todo objects with the same id should be equal, regardless of other fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_inequality_by_different_id() -> None:
    """Todo objects with different ids should not be equal, even with same text."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_not_equal_to_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk")

    assert todo != 1, "Todo should not equal an integer"
    assert todo != "buy milk", "Todo should not equal a string"
    assert todo != {"id": 1, "text": "buy milk"}, "Todo should not equal a dict"
    assert todo is not None, "Todo should not equal None"


def test_todo_hash_consistent() -> None:
    """Todo hash should be based on id and consistent."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)

    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_hash_different_for_different_id() -> None:
    """Todo hash should be different for different ids."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")

    assert hash(todo1) != hash(todo2), "Todos with different ids should have different hashes"


def test_todo_in_set() -> None:
    """Todo objects can be added to a set with deduplication by id."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")  # Same id, different content
    todo3 = Todo(id=2, text="buy eggs")

    todo_set = {todo1, todo2, todo3}

    assert len(todo_set) == 2, "Set should contain 2 unique todos (by id)"


def test_todo_as_dict_key() -> None:
    """Todo objects can be used as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")  # Same id as todo1

    todo_dict = {todo1: "value1"}

    # Since todo2 has same id as todo1, it should be the same key
    todo_dict[todo2] = "value2"

    assert len(todo_dict) == 1, "Dict should have only 1 key (todos with same id)"
    assert todo_dict[todo1] == "value2", "Value should be updated for same-id todo"


def test_todo_reflexivity() -> None:
    """Todo equality should be reflexive (x == x)."""
    todo = Todo(id=1, text="buy milk")
    assert todo == todo, "Todo should equal itself"


def test_todo_symmetry() -> None:
    """Todo equality should be symmetric (x == y implies y == x)."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")

    assert todo1 == todo2, "todo1 should equal todo2"
    assert todo2 == todo1, "todo2 should equal todo1"


def test_todo_transitivity() -> None:
    """Todo equality should be transitive (x == y and y == z implies x == z)."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")
    todo3 = Todo(id=1, text="buy eggs")

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3, "Equality should be transitive"
