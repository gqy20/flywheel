"""Tests for Todo.__hash__ method (Issue #6620).

These tests verify that:
1. Todo objects can be hashed (used in sets and as dict keys)
2. Hash is based on id field for identity semantics
3. Todos with same id deduplicate in sets
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
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy bread")

    todo_set = {todo1, todo2}

    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_can_be_used_as_dict_key() -> None:
    """Todo objects should be usable as dict keys."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy bread")

    todo_dict = {todo1: "task1", todo2: "task2"}

    assert todo_dict[todo1] == "task1"
    assert todo_dict[todo2] == "task2"


def test_todo_deduplication_by_id() -> None:
    """Todos with same id should deduplicate in sets (id-based identity)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)  # Same id, different done

    todo_set = {todo1, todo2}

    # Should deduplicate to 1 item based on id
    assert len(todo_set) == 1


def test_todo_hash_consistency() -> None:
    """Hash should be consistent for same id."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")

    # Same id should produce same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_for_different_ids() -> None:
    """Hash should be different for different ids."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")

    # Different ids should (likely) produce different hashes
    # Note: hash collisions are theoretically possible but unlikely
    assert hash(todo1) != hash(todo2)
