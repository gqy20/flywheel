"""Tests for Todo.__hash__ method (Issue #4064).

These tests verify that:
1. Todo objects can be hashed (used in sets, as dict keys)
2. Hash is based on the id field
3. Todos with same id hash to same value (deduplication in sets)
4. Hash is stable across multiple calls
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_hash_returns_int() -> None:
    """hash(Todo) should return an integer without raising TypeError."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = hash(todo)

    # Should return an integer
    assert isinstance(result, int)


def test_todo_hash_based_on_id() -> None:
    """Todo hash should be based on the id field."""
    todo_id = 42
    todo = Todo(id=todo_id, text="test task")
    result = hash(todo)

    # Hash should match hash of the id
    assert result == hash(todo_id)


def test_todo_hash_consistent() -> None:
    """Todo hash should be stable across multiple calls."""
    todo = Todo(id=1, text="stable hash")

    hash1 = hash(todo)
    hash2 = hash(todo)

    assert hash1 == hash2


def test_todo_hash_different_ids_different_hashes() -> None:
    """Todos with different ids should have different hashes."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")

    assert hash(todo1) != hash(todo2)


def test_todo_set_deduplication_identical() -> None:
    """Identical Todos (same all fields) should deduplicate in a set."""
    # Provide explicit timestamps to ensure true equality
    timestamp = "2026-01-01T00:00:00+00:00"
    todo1 = Todo(id=1, text="task", done=False, created_at=timestamp, updated_at=timestamp)
    todo2 = Todo(id=1, text="task", done=False, created_at=timestamp, updated_at=timestamp)

    todo_set = {todo1, todo2}

    # Both are identical - so set should have only 1 element
    assert len(todo_set) == 1


def test_todo_set_same_id_different_fields() -> None:
    """Todos with same id but different fields are distinct in set.

    Note: Dataclass eq=True compares all fields, not just id.
    Two Todos with same id but different text/done are NOT equal.
    """
    todo1 = Todo(id=1, text="first", done=False)
    todo2 = Todo(id=1, text="second", done=True)

    todo_set = {todo1, todo2}

    # Same id but different content = distinct objects in set
    assert len(todo_set) == 2


def test_todo_set_different_ids() -> None:
    """Todos with different ids should both be in a set."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    todo_set = {todo1, todo2}

    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_as_dict_key() -> None:
    """Todo should work as a dictionary key."""
    todo = Todo(id=1, text="my task")
    todo_dict = {todo: "value"}

    assert todo_dict[todo] == "value"
    assert todo in todo_dict


def test_todo_dict_key_identical() -> None:
    """Identical Todos should map to same dict entry."""
    # Provide explicit timestamps to ensure true equality
    timestamp = "2026-01-01T00:00:00+00:00"
    todo1 = Todo(id=1, text="task", created_at=timestamp, updated_at=timestamp)
    todo2 = Todo(id=1, text="task", created_at=timestamp, updated_at=timestamp)

    todo_dict = {todo1: "value"}

    # Same all fields - should find existing entry
    assert todo_dict.get(todo2) == "value"
