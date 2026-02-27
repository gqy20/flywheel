"""Tests for issue #6095: Add Todo hash support for set and dict operations."""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_hash_returns_integer() -> None:
    """hash(Todo) should return an integer without raising TypeError."""
    todo = Todo(id=1, text="test todo")
    # This should not raise TypeError
    result = hash(todo)
    assert isinstance(result, int)


def test_todo_set_deduplication_by_id() -> None:
    """Todo objects with same id should be deduplicated in a set."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")  # Same id, different text
    todo3 = Todo(id=2, text="third")  # Different id

    todo_set = {todo1, todo2, todo3}

    # Should have 2 items: id=1 and id=2 (todos with same id are considered equal)
    assert len(todo_set) == 2


def test_todo_as_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    todo_dict = {todo1: "value1", todo2: "value2"}

    assert todo_dict[todo1] == "value1"
    assert todo_dict[todo2] == "value2"
    assert len(todo_dict) == 2


def test_todo_hash_consistency() -> None:
    """hash(Todo) should return consistent values for same id."""
    todo1 = Todo(id=42, text="test")
    todo2 = Todo(id=42, text="different text")

    # Todos with same id should have same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_for_different_ids() -> None:
    """hash(Todo) should typically differ for different ids."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")

    # While hash collisions are possible, ids 1 and 2 should not collide
    assert hash(todo1) != hash(todo2)
