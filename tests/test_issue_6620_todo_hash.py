"""Tests for Todo.__hash__ method (Issue #6620).

These tests verify that:
1. Todo objects can be hashed (used in sets)
2. Todo objects can be used as dict keys
3. Hash is based on id field for id-based identity semantics
4. Todos with same id are deduplicated in sets
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_is_hashable() -> None:
    """hash(Todo) should not raise TypeError."""
    todo = Todo(id=1, text="buy milk", done=False)
    # Should not raise TypeError
    hash(todo)


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be addable to a set."""
    todo = Todo(id=1, text="buy milk", done=False)
    todo_set = {todo}
    assert len(todo_set) == 1
    assert todo in todo_set


def test_todo_can_be_used_as_dict_key() -> None:
    """Todo objects should be usable as dict keys."""
    todo = Todo(id=1, text="buy milk", done=False)
    todo_dict = {todo: "value"}
    assert todo_dict[todo] == "value"


def test_todo_set_deduplication_by_id() -> None:
    """Todos with same id should be deduplicated in a set.

    Since hash is based on id, two Todo objects with the same id
    should be considered equal in a set context.
    """
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)  # Same id, different text/done

    # Both should have same hash (based on id)
    assert hash(todo1) == hash(todo2)

    # Set should contain only one item (deduplication)
    todo_set = {todo1, todo2}
    assert len(todo_set) == 1, f"Expected 1 item in set, got {len(todo_set)}"


def test_todo_hash_based_on_id() -> None:
    """Todo hash should be based on id field."""
    todo1 = Todo(id=42, text="task a", done=False)
    todo2 = Todo(id=42, text="task b", done=True)

    # Same id should produce same hash
    assert hash(todo1) == hash(todo2)

    # Different id should produce different hash
    todo3 = Todo(id=99, text="task a", done=False)
    assert hash(todo1) != hash(todo3)


def test_todo_hash_stable() -> None:
    """Todo hash should be stable across multiple calls."""
    todo = Todo(id=1, text="buy milk", done=False)
    hash1 = hash(todo)
    hash2 = hash(todo)
    hash3 = hash(todo)

    assert hash1 == hash2 == hash3


def test_todo_hash_different_ids() -> None:
    """Todos with different ids should have different hashes."""
    todos = [Todo(id=i, text=f"task {i}") for i in range(10)]
    hashes = [hash(t) for t in todos]

    # All hashes should be unique (with high probability)
    assert len(set(hashes)) == 10, "Expected unique hashes for unique ids"
