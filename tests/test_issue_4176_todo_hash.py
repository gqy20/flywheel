"""Tests for Todo.__hash__ method (Issue #4176).

These tests verify that:
1. hash(Todo) does not raise TypeError
2. Todo objects can be added to a set
3. Same id produces same hash
4. Todo objects can be used as dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_is_hashable() -> None:
    """hash(Todo) should not raise TypeError."""
    todo = Todo(id=1, text="test")
    # Should not raise TypeError
    result = hash(todo)
    assert isinstance(result, int)


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be addable to a set."""
    todo = Todo(id=1, text="test")
    todo_set = {todo}
    assert len(todo_set) == 1
    assert todo in todo_set


def test_same_id_produces_same_hash() -> None:
    """Todos with same id should have same hash."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    assert hash(todo1) == hash(todo2)


def test_set_deduplication_by_id() -> None:
    """Set with same-id todos should deduplicate (issue acceptance criteria)."""
    todo_set = {Todo(id=1, text="a"), Todo(id=1, text="a")}
    assert len(todo_set) == 1


def test_todo_as_dict_key() -> None:
    """Todo objects should be usable as dict keys (issue acceptance criteria)."""
    d = {Todo(id=1, text="a"): "value"}
    # Same id, different text should still find the key
    assert d[Todo(id=1, text="b")] == "value"


def test_different_ids_different_hashes() -> None:
    """Todos with different ids should have different hashes."""
    todo1 = Todo(id=1, text="test")
    todo2 = Todo(id=2, text="test")
    # Hashes are likely different (not guaranteed, but should be for different ids)
    # The key property is that they can coexist in a set
    todo_set = {todo1, todo2}
    assert len(todo_set) == 2
