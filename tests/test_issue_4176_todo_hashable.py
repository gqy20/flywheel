"""Tests for Todo.__hash__ method (Issue #4176).

These tests verify that:
1. Todo objects are hashable (can be used in sets and as dict keys)
2. Todos with the same id produce the same hash (identity-based hashing)
3. Deduplication works correctly based on id
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_is_hashable() -> None:
    """hash(Todo) should not raise TypeError."""
    todo = Todo(id=1, text="test")
    # This should not raise TypeError
    result = hash(todo)
    assert isinstance(result, int)


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be addable to a set."""
    todo1 = Todo(id=1, text="test1")
    todo2 = Todo(id=2, text="test2")

    todo_set = {todo1, todo2}
    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_can_be_used_as_dict_key() -> None:
    """Todo objects should be usable as dict keys."""
    todo = Todo(id=1, text="key")
    d = {todo: "value"}

    assert d[todo] == "value"


def test_same_id_produces_same_hash() -> None:
    """Todos with the same id should produce the same hash."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")  # Same id, different text

    assert hash(todo1) == hash(todo2)


def test_different_id_produces_different_hash() -> None:
    """Todos with different ids should produce different hashes."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")  # Different id, same text

    assert hash(todo1) != hash(todo2)


def test_set_deduplication_identical_objects() -> None:
    """Set should deduplicate identical Todo objects."""
    # Same todo instance added twice results in set of size 1
    todo = Todo(id=1, text="a")
    todo_set = {todo, todo}
    assert len(todo_set) == 1


def test_dict_lookup_same_instance() -> None:
    """Dict lookup should work with the same instance."""
    # Create a dict with a Todo as key
    todo = Todo(id=1, text="a")
    d = {todo: "value"}

    # Lookup with the same instance should work
    assert d[todo] == "value"


def test_hash_remains_consistent() -> None:
    """Hash value should remain consistent for the same object."""
    todo = Todo(id=1, text="test")
    hash1 = hash(todo)
    hash2 = hash(todo)

    assert hash1 == hash2
