"""Tests for Todo.__hash__ method (Issue #6327).

These tests verify that:
1. Todo objects can be hashed (hash() returns int without error)
2. Two Todo objects with same id have same hash
3. Todo objects can be used in sets for deduplication
4. Todo objects can be used as dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_hash_returns_int() -> None:
    """hash(Todo) should return an int without raising TypeError."""
    todo = Todo(id=1, text="test task")
    result = hash(todo)

    assert isinstance(result, int)


def test_todo_same_id_same_hash() -> None:
    """Two Todo objects with same id should have same hash."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=1, text="task two")

    assert hash(todo1) == hash(todo2)


def test_todo_different_id_different_hash() -> None:
    """Todo objects with different ids should have different hashes."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")

    # Different ids should produce different hashes
    assert hash(todo1) != hash(todo2)


def test_todo_can_be_added_to_set() -> None:
    """Todo objects can be added to a set."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")

    todo_set = {todo1, todo2}

    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_set_deduplication_by_id() -> None:
    """Set with Todos having same id should deduplicate to single item."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=1, text="task two")  # Same id, different text

    todo_set = {todo1, todo2}

    # Should deduplicate based on hash (which is based on id)
    assert len(todo_set) == 1


def test_todo_can_be_dict_key() -> None:
    """Todo objects can be used as dict keys."""
    todo = Todo(id=1, text="task")
    mapping = {todo: "value"}

    assert mapping[todo] == "value"


def test_todo_dict_lookup_by_hash() -> None:
    """Dict lookup with Todo having same id should find the key."""
    todo1 = Todo(id=1, text="original")
    todo2 = Todo(id=1, text="same id")  # Same id, different object

    mapping = {todo1: "stored value"}

    # Since hash is based on id, todo2 should hash to same value
    # and be able to retrieve the value
    assert mapping.get(todo2) == "stored value"


def test_todo_hash_consistent_across_calls() -> None:
    """Hash should be consistent across multiple calls on same object."""
    todo = Todo(id=42, text="consistent")

    hash1 = hash(todo)
    hash2 = hash(todo)
    hash3 = hash(todo)

    assert hash1 == hash2 == hash3
