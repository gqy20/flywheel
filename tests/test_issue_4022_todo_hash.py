"""Tests for Todo.__hash__ method (Issue #4022).

These tests verify that:
1. hash(Todo) returns a consistent integer value
2. Todo objects with same id have same hash
3. Todo objects can be added to a set
4. Todo objects can be used as dictionary keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_hash_returns_integer() -> None:
    """hash(Todo) should return an integer."""
    todo = Todo(id=1, text="test task")
    result = hash(todo)

    assert isinstance(result, int)


def test_todo_hash_is_consistent() -> None:
    """hash(Todo) should return the same value on multiple calls."""
    todo = Todo(id=1, text="test task")
    hash1 = hash(todo)
    hash2 = hash(todo)

    assert hash1 == hash2


def test_todo_hash_based_on_id() -> None:
    """Todo objects with same id should have same hash regardless of other fields."""
    t1 = Todo(id=1, text="task a", done=False)
    t2 = Todo(id=1, text="task b", done=True)

    assert hash(t1) == hash(t2)


def test_todo_hash_different_for_different_ids() -> None:
    """Todo objects with different ids should likely have different hashes."""
    t1 = Todo(id=1, text="same text")
    t2 = Todo(id=2, text="same text")

    # While not guaranteed, it's highly likely different ids produce different hashes
    assert hash(t1) != hash(t2)


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be usable in a set."""
    t1 = Todo(id=1, text="task a")
    t2 = Todo(id=2, text="task b")

    todo_set = {t1, t2}

    assert len(todo_set) == 2
    assert t1 in todo_set
    assert t2 in todo_set


def test_todo_set_deduplication_by_id() -> None:
    """Set should deduplicate Todo objects with same id."""
    t1 = Todo(id=1, text="task a")
    t2 = Todo(id=1, text="task b")

    # Todos with same id should be considered equal for set purposes
    todo_set = {t1, t2}

    assert len(todo_set) == 1


def test_todo_can_be_used_as_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo = Todo(id=1, text="my task")
    todo_dict = {todo: "value"}

    assert todo_dict[todo] == "value"


def test_todo_dict_lookup_by_hash() -> None:
    """Todo dictionary lookup should work based on id/hash."""
    t1 = Todo(id=1, text="original")
    t2 = Todo(id=1, text="modified")

    # Both todos have same id, so they should be treated as same key
    todo_dict = {t1: "first_value"}
    todo_dict[t2] = "second_value"

    # Should have only one entry since they have same id
    assert len(todo_dict) == 1
