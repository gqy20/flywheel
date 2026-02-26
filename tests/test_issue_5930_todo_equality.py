"""Tests for Todo.__eq__ and __hash__ methods (Issue #5930).

These tests verify that:
1. Todo objects with the same id are equal regardless of other fields
2. Todo objects with different ids are not equal
3. Todo objects with the same id have the same hash (for set/dict usage)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_based_on_id_only() -> None:
    """Todo(id=1, text='a') == Todo(id=1, text='b') should return True."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="b", done=True)

    # Same id should be equal regardless of text/done differences
    assert todo1 == todo2


def test_todo_inequality_based_on_different_id() -> None:
    """Todo(id=1, text='a') != Todo(id=2, text='a') should return True."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")

    # Different id should not be equal even with same text
    assert todo1 != todo2


def test_todo_hash_based_on_id() -> None:
    """hash(Todo(id=1, text='a')) == hash(Todo(id=1, text='b')) should return True."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    # Same id should produce same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_allows_set_operations() -> None:
    """Todo objects with same id should be treated as same in set."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")
    todo3 = Todo(id=2, text="third")

    # Set should deduplicate based on id
    todo_set = {todo1, todo2, todo3}

    # Should have only 2 items: id=1 and id=2
    assert len(todo_set) == 2


def test_todo_hash_allows_dict_operations() -> None:
    """Todo objects with same id should work as dict keys."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")

    # Using todos as dict keys
    mapping = {todo1: "value1"}
    mapping[todo2] = "value2"

    # Should have only 1 entry since both have same id
    assert len(mapping) == 1
    # The value should be overwritten
    assert mapping[todo1] == "value2"


def test_todo_equality_with_none() -> None:
    """Todo should not be equal to None or other types."""
    todo = Todo(id=1, text="test")

    assert todo != None  # noqa: E711
    assert todo != "not a todo"
    assert todo != 1


def test_todo_reflexive_equality() -> None:
    """A Todo should be equal to itself."""
    todo = Todo(id=1, text="test")
    assert todo == todo
