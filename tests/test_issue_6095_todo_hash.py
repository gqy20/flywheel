"""Tests for Todo hash support (Issue #6095).

These tests verify that:
1. Todo objects are hashable (hash(todo) returns an integer)
2. Todo objects can be added to sets
3. Todo objects with same id are deduplicated in sets
4. Todo objects can be used as dictionary keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_is_hashable() -> None:
    """hash(Todo) should return an integer without raising TypeError."""
    todo = Todo(id=1, text="test task")
    # Should not raise TypeError
    result = hash(todo)
    assert isinstance(result, int)


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be addable to a set."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")

    todo_set = {todo1, todo2}
    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_set_deduplication_by_id() -> None:
    """Set should deduplicate Todo objects with the same id."""
    todo1 = Todo(id=1, text="original text")
    todo2 = Todo(id=1, text="different text")

    # Both have same id, so should be considered equal for set purposes
    todo_set = {todo1, todo2}
    # After implementing __hash__ based on id, these should deduplicate
    assert len(todo_set) == 1, "Todos with same id should deduplicate in set"


def test_todo_can_be_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo = Todo(id=1, text="test task")
    todo_dict = {todo: "some value"}

    assert todo_dict[todo] == "some value"
    assert todo in todo_dict


def test_todo_dict_lookup_by_id() -> None:
    """Dict should find Todo by same-id object as key."""
    todo1 = Todo(id=1, text="original")
    todo2 = Todo(id=1, text="same id")

    todo_dict = {todo1: "value"}

    # With hash based on id, todo2 should match todo1 as a key
    assert todo_dict.get(todo2) == "value", "Dict should find value using same-id Todo"


def test_todo_hash_consistency() -> None:
    """hash(Todo) should return same value for same id."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")

    # Hashes should be equal for same id
    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_hash_differs_for_different_ids() -> None:
    """hash(Todo) should likely differ for different ids."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")

    # Hashes should likely be different for different ids
    # (not strictly required but expected behavior)
    assert hash(todo1) != hash(todo2), "Todos with different ids should have different hashes"
