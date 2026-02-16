"""Tests for Todo.__eq__ and __hash__ methods (Issue #3750).

These tests verify that:
1. Todo objects with the same id are equal regardless of other fields
2. Todo objects with different ids are not equal
3. hash(Todo) is consistent with equality (same id = same hash)
4. Todo objects can be used in sets and as dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_by_id() -> None:
    """Todo objects with the same id should be equal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="b", done=True)
    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_inequality_different_id() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")
    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_hash_consistent() -> None:
    """Hash should be consistent with equality (same id = same hash)."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_set_deduplication() -> None:
    """Todo objects can be used in sets for deduplication by id."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")  # Same id as todo1
    todo3 = Todo(id=2, text="c")

    todo_set = {todo1, todo2, todo3}
    assert len(todo_set) == 2, f"Set should have 2 unique todos by id, got {len(todo_set)}"


def test_todo_as_dict_key() -> None:
    """Todo objects can be used as dictionary keys."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")  # Same id as todo1

    d = {todo1: "value1"}
    d[todo2] = "value2"  # Should overwrite value1 because same id

    assert len(d) == 1, "Dict should have 1 key"
    assert d[todo1] == "value2", "Value should be overwritten"


def test_todo_hash_stable() -> None:
    """Hash should be stable across multiple calls."""
    todo = Todo(id=42, text="test")
    hash1 = hash(todo)
    hash2 = hash(todo)
    assert hash1 == hash2, "Hash should be stable"


def test_todo_not_equal_to_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="test")
    assert todo != 1, "Todo should not equal an int"
    assert todo != "test", "Todo should not equal a string"
    assert todo != {"id": 1}, "Todo should not equal a dict"
