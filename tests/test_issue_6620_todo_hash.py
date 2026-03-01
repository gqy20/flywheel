"""Tests for Todo.__hash__ method (Issue #6620).

These tests verify that:
1. Todo objects can be hashed (used in sets and as dict keys)
2. Hash is based on id field for id-based identity semantics
3. Todos with same id are deduplicated in sets
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_is_hashable() -> None:
    """hash(Todo) should not raise TypeError."""
    todo = Todo(id=1, text="buy milk", done=False)
    # This should not raise TypeError
    result = hash(todo)
    assert isinstance(result, int)


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


def test_todo_deduplication_in_set() -> None:
    """Todos with same id should be deduplicated in sets (id-based identity)."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")  # Same id, different text
    
    todo_set = {todo1, todo2}
    # Since hash is based on id, both should be considered equal for set purposes
    assert len(todo_set) == 1, f"Expected 1 item in set, got {len(todo_set)}"


def test_todo_hash_based_on_id() -> None:
    """Hash should be based on id field."""
    todo1 = Todo(id=42, text="task a")
    todo2 = Todo(id=42, text="task b")  # Same id, different text
    
    # Same id should produce same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_stability() -> None:
    """Hash should be stable across multiple calls."""
    todo = Todo(id=1, text="buy milk")
    hash1 = hash(todo)
    hash2 = hash(todo)
    hash3 = hash(todo)
    
    assert hash1 == hash2 == hash3


def test_todo_different_ids_different_hashes() -> None:
    """Todos with different ids should have different hashes."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")
    
    # Different ids should produce different hashes (with high probability)
    assert hash(todo1) != hash(todo2)
