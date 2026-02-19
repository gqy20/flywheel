"""Tests for Todo.__eq__ and __hash__ methods (Issue #4468).

These tests verify that:
1. Todo equality is based on id field only
2. Todo objects can be hashed and used in sets/dicts
3. hash(Todo) is consistent for objects with same id
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_based_on_id() -> None:
    """Todo equality should be based on id field only."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy eggs", done=True)  # Same id, different other fields
    todo3 = Todo(id=2, text="buy milk", done=False)  # Different id, same other fields

    # Same id should be equal
    assert todo1 == todo2, "Todos with same id should be equal"

    # Different id should not be equal
    assert todo1 != todo3, "Todos with different id should not be equal"


def test_todo_equality_with_non_todo() -> None:
    """Todo equality with non-Todo objects should return False."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != 1, "Todo should not equal an int with same id value"
    assert todo != "Todo", "Todo should not equal a string"
    assert todo != {"id": 1}, "Todo should not equal a dict"
    assert todo is not None, "Todo should not equal None"


def test_todo_hash_consistent() -> None:
    """hash(Todo) should be consistent for objects with same id."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy eggs", done=True)  # Same id, different other fields

    # Same id should have same hash
    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_hash_different_for_different_ids() -> None:
    """hash(Todo) should be different for objects with different ids (usually)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    # Different ids should typically have different hashes
    # Note: hash collisions are possible but rare
    assert hash(todo1) != hash(todo2), "Todos with different ids should have different hashes"


def test_todo_in_set() -> None:
    """Todo objects can be added to a set and deduplicated by id."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy eggs", done=True)  # Same id, different content
    todo3 = Todo(id=2, text="buy bread", done=False)

    todo_set = {todo1, todo2, todo3}

    # Set should have 2 items (todo1 and todo2 are same id, so deduplicated)
    assert len(todo_set) == 2, f"Set should have 2 unique todos by id, got {len(todo_set)}"


def test_todo_as_dict_key() -> None:
    """Todo objects can be used as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy eggs", done=True)  # Same id, different content
    todo3 = Todo(id=2, text="buy bread", done=False)

    # Use todos as dict keys
    todo_dict = {todo1: "first", todo3: "third"}

    # todo2 should be treated as same key as todo1 (same id)
    assert todo_dict[todo2] == "first", "Same-id todo should find same dict entry"

    # todo3 should have its own entry
    assert todo_dict[todo3] == "third"


def test_todo_hash_stable() -> None:
    """hash(Todo) should be stable across multiple calls."""
    todo = Todo(id=1, text="buy milk", done=False)

    hash1 = hash(todo)
    hash2 = hash(todo)
    hash3 = hash(todo)

    assert hash1 == hash2 == hash3, "hash should be stable across calls"
