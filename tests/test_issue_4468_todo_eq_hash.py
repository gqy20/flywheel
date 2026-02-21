"""Tests for Todo.__eq__ and __hash__ methods (Issue #4468).

These tests verify that Todo objects can be compared and used in sets/dicts
based on their unique id field.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_based_on_id() -> None:
    """Issue #4468: Todo equality should be based on id field."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    # Different text, same id -> should be equal
    assert todo1 == todo2


def test_todo_inequality_different_id() -> None:
    """Issue #4468: Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")

    # Same text, different id -> should NOT be equal
    assert todo1 != todo2


def test_todo_hash_consistent() -> None:
    """Issue #4468: Hash should be based on id and consistent."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    # Same id should have same hash
    assert hash(todo1) == hash(todo2)


def test_todo_in_set() -> None:
    """Issue #4468: Todo should be usable in a set and deduplicate by id."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")  # Same id as todo1
    todo3 = Todo(id=2, text="third")

    todo_set = {todo1, todo2, todo3}

    # Should deduplicate based on id (only 2 unique ids)
    assert len(todo_set) == 2


def test_todo_as_dict_key() -> None:
    """Issue #4468: Todo should be usable as a dict key."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")  # Same id, different text

    mapping = {todo1: "value1"}

    # Same id should map to same key
    assert mapping[todo2] == "value1"


def test_todo_equality_with_non_todo() -> None:
    """Issue #4468: Comparing Todo with non-Todo should return False."""
    todo = Todo(id=1, text="a")

    # Should not be equal to non-Todo objects
    assert todo != 1
    assert todo != "1"
    assert todo != {"id": 1, "text": "a"}
    assert todo is not None
