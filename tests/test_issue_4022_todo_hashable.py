"""Tests for Todo.__hash__ method (Issue #4022).

These tests verify that:
1. Todo objects are hashable and can be used in sets/dicts
2. hash(Todo) is consistent and based on the id field
3. Todos with the same id have the same hash
4. Todos can be deduplicated in sets by id
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_is_hashable() -> None:
    """Todo objects should be hashable."""
    todo = Todo(id=1, text="buy milk", done=False)
    # Should not raise TypeError
    hash_value = hash(todo)
    assert isinstance(hash_value, int)


def test_todo_hash_is_consistent() -> None:
    """hash(Todo) should return consistent value for same object."""
    todo = Todo(id=1, text="buy milk", done=False)
    hash1 = hash(todo)
    hash2 = hash(todo)
    assert hash1 == hash2


def test_todo_hash_based_on_id() -> None:
    """Todos with same id should have same hash, regardless of other fields."""
    t1 = Todo(id=1, text="buy milk", done=False)
    t2 = Todo(id=1, text="different text", done=True)
    assert hash(t1) == hash(t2)


def test_todo_different_id_different_hash() -> None:
    """Todos with different ids should have different hashes."""
    t1 = Todo(id=1, text="task one")
    t2 = Todo(id=2, text="task two")
    # Different ids should produce different hashes
    assert hash(t1) != hash(t2)


def test_todo_can_be_in_set() -> None:
    """Todo objects should be addable to a set."""
    t1 = Todo(id=1, text="buy milk")
    t2 = Todo(id=2, text="buy eggs")
    todo_set = {t1, t2}
    assert len(todo_set) == 2
    assert t1 in todo_set
    assert t2 in todo_set


def test_todo_set_deduplication_by_id() -> None:
    """Todos with same id should deduplicate in a set."""
    t1 = Todo(id=1, text="buy milk", done=False)
    t2 = Todo(id=1, text="different text", done=True)
    # Both have id=1, so set should have only 1 element
    todo_set = {t1, t2}
    assert len(todo_set) == 1


def test_todo_can_be_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    t1 = Todo(id=1, text="task one")
    t2 = Todo(id=2, text="task two")
    todo_dict = {t1: "value1", t2: "value2"}
    assert todo_dict[t1] == "value1"
    assert todo_dict[t2] == "value2"
