"""Tests for Todo.__hash__ method (Issue #4022).

These tests verify that:
1. Todo objects can be hashed consistently
2. Todo objects with same id have same hash
3. Todo objects can be added to a set
4. Todo objects can be used as dictionary keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_hash_consistent() -> None:
    """hash(Todo) should return consistent value for same id."""
    todo = Todo(id=1, text="buy milk", done=False)
    hash1 = hash(todo)
    hash2 = hash(todo)
    assert hash1 == hash2, "hash should be consistent"


def test_todo_hash_based_on_id() -> None:
    """Todos with same id should have same hash regardless of other fields."""
    t1 = Todo(id=1, text="buy milk", done=False)
    t2 = Todo(id=1, text="different text", done=True)
    assert hash(t1) == hash(t2), "hash should be based on id only"


def test_todo_different_id_different_hash() -> None:
    """Todos with different ids should have different hashes."""
    t1 = Todo(id=1, text="task one")
    t2 = Todo(id=2, text="task one")
    assert hash(t1) != hash(t2), "different ids should have different hashes"


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be addable to a set."""
    t1 = Todo(id=1, text="task one")
    t2 = Todo(id=2, text="task two")
    todo_set = {t1, t2}
    assert len(todo_set) == 2
    assert t1 in todo_set
    assert t2 in todo_set


def test_todo_set_deduplication_by_id() -> None:
    """Set should deduplicate todos with same id."""
    t1 = Todo(id=1, text="buy milk", done=False)
    t2 = Todo(id=1, text="different text", done=True)
    todo_set = {t1, t2}
    assert len(todo_set) == 1, "todos with same id should be deduplicated in a set"


def test_todo_can_be_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    t1 = Todo(id=1, text="task one")
    t2 = Todo(id=2, text="task two")
    mapping = {t1: "first", t2: "second"}
    assert mapping[t1] == "first"
    assert mapping[t2] == "second"


def test_todo_dict_key_lookup_by_id() -> None:
    """Dict should treat todos with same id as same key."""
    t1 = Todo(id=1, text="buy milk", done=False)
    t2 = Todo(id=1, text="different text", done=True)
    mapping = {t1: "value"}
    assert mapping[t2] == "value", "lookup should work with different todo having same id"
