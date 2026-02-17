"""Tests for Todo.__hash__ method (Issue #4064).

These tests verify that:
1. Todo objects can be hashed
2. Todos with the same id are considered equal in sets
3. Todos can be used as dictionary keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_hash_not_raises() -> None:
    """hash(Todo) should not raise TypeError."""
    todo = Todo(id=1, text="test todo")
    # This should not raise TypeError
    result = hash(todo)
    assert isinstance(result, int)


def test_todo_hash_based_on_id() -> None:
    """hash(Todo) should be based on the id field."""
    todo1 = Todo(id=42, text="first")
    todo2 = Todo(id=42, text="second")
    # Same id should produce same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_ids() -> None:
    """Todos with different ids should have different hashes."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")
    # Different ids should (likely) produce different hashes
    assert hash(todo1) != hash(todo2)


def test_todo_set_deduplication() -> None:
    """Todos with same id should deduplicate in a set."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")
    todo_set = {todo1, todo2}
    # Same id should result in only one element
    assert len(todo_set) == 1


def test_todo_set_with_different_ids() -> None:
    """Todos with different ids should both be in a set."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")
    todo_set = {todo1, todo2}
    assert len(todo_set) == 2


def test_todo_as_dict_key() -> None:
    """Todo should be usable as a dictionary key."""
    todo = Todo(id=1, text="test todo")
    # This should not raise TypeError
    mapping = {todo: "value"}
    assert mapping[todo] == "value"


def test_todo_dict_key_with_same_id() -> None:
    """Todos with same id should access the same dict entry."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")
    mapping = {todo1: "original"}
    # Since same id, todo2 should find the same entry
    assert mapping[todo2] == "original"


def test_todo_hash_consistent_after_mutation() -> None:
    """hash(Todo) should remain consistent even after mutation."""
    todo = Todo(id=1, text="original")
    original_hash = hash(todo)

    # Mutate the todo
    todo.mark_done()
    assert hash(todo) == original_hash

    todo.rename("renamed")
    assert hash(todo) == original_hash
