"""Tests for Todo.__eq__ and __hash__ methods (Issue #3750).

These tests verify that:
1. Todo objects are compared by id for equality
2. Todo objects with same id are considered equal regardless of other fields
3. Todo objects can be used in sets for deduplication
4. Todo objects can be used as dictionary keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_by_id() -> None:
    """Todo objects with same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="b", done=True)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_inequality_different_id() -> None:
    """Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="same text", done=True)
    todo2 = Todo(id=2, text="same text", done=True)

    assert todo1 != todo2, "Todos with different id should not be equal"


def test_todo_hash_consistent() -> None:
    """Todo objects with same id should have same hash."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_set_deduplication() -> None:
    """Todo objects should be deduplicated in sets by id."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    todo3 = Todo(id=2, text="c")

    todo_set = {todo1, todo2, todo3}

    assert len(todo_set) == 2, "Set should contain 2 unique todos by id"
    assert todo1 in todo_set
    assert todo2 in todo_set  # Same id as todo1
    assert todo3 in todo_set


def test_todo_dict_key_usage() -> None:
    """Todo objects should work as dictionary keys."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")  # Same id as todo1

    d = {todo1: "value1"}
    d[todo2] = "value2"  # Should overwrite due to same id

    assert len(d) == 1, "Dict should have 1 entry"
    assert d[todo1] == "value2", "Value should be overwritten"


def test_todo_eq_with_non_todo() -> None:
    """Todo equality with non-Todo should return NotImplemented/False."""
    todo = Todo(id=1, text="a")

    # Comparing Todo to non-Todo should not raise and should return False
    assert todo != 1
    assert todo != "1"
    assert todo != {"id": 1, "text": "a"}
    assert todo is not None


def test_todo_hash_different_ids() -> None:
    """Todo objects with different id should likely have different hashes."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")

    # Hash collisions are theoretically possible but unlikely for consecutive ints
    # This test verifies the basic behavior
    assert hash(todo1) != hash(todo2), "Different ids should produce different hashes"
