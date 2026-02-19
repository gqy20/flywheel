"""Tests for Todo.__hash__ method (Issue #4588).

These tests verify that:
1. hash(Todo) returns a consistent integer
2. Todo objects can be added to a set
3. Todo objects with same id hash to the same value
4. Todo objects can be used as dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_hash_returns_int() -> None:
    """hash(Todo) should return an integer."""
    todo = Todo(id=1, text="test task")
    result = hash(todo)

    assert isinstance(result, int)


def test_todo_hash_is_consistent() -> None:
    """hash(Todo) should return the same value for same id."""
    todo1 = Todo(id=1, text="first task")
    todo2 = Todo(id=1, text="different text")

    # Same id should hash to same value
    assert hash(todo1) == hash(todo2)


def test_todo_hash_differs_for_different_ids() -> None:
    """hash(Todo) should differ for different ids (with high probability)."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")

    # Different ids should (very likely) have different hashes
    assert hash(todo1) != hash(todo2)


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be storable in a set."""
    todo1 = Todo(id=1, text="first task")
    todo2 = Todo(id=2, text="second task")

    todo_set = {todo1, todo2}

    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_set_deduplication_by_id() -> None:
    """Todo objects with same id should be deduplicated in a set."""
    todo1 = Todo(id=1, text="first task")
    todo2 = Todo(id=1, text="different text")

    # Both have id=1, should be treated as same in set
    todo_set = {todo1, todo2}

    assert len(todo_set) == 1


def test_todo_can_be_dict_key() -> None:
    """Todo objects should be usable as dict keys."""
    todo = Todo(id=1, text="my task")
    mapping = {todo: "task value"}

    assert mapping[todo] == "task value"


def test_todo_dict_key_lookup_by_hash() -> None:
    """Dict lookup should work for Todo objects with same id."""
    todo1 = Todo(id=1, text="original")
    todo2 = Todo(id=1, text="updated text")

    mapping = {todo1: "value"}

    # todo2 has same id, so it should find the same key
    assert mapping[todo2] == "value"
