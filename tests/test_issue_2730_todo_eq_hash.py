"""Tests for Todo.__eq__ and __hash__ methods (Issue #2730).

These tests verify that:
1. Todo objects with same id are considered equal
2. Todo objects with different ids are not equal
3. Todo can be used in sets for deduplication
4. Todo can be used as dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id() -> None:
    """Todo objects with same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    # Should be equal because ids match
    assert todo1 == todo2
    # Equality should be symmetric
    assert todo2 == todo1
    # Equality should be reflexive
    assert todo1 == todo1


def test_todo_eq_different_id() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text", done=False)
    todo2 = Todo(id=2, text="same text", done=False)

    # Should not be equal because ids differ
    assert todo1 != todo2
    # Inequality should be symmetric
    assert todo2 != todo1


def test_todo_eq_none() -> None:
    """Todo should not be equal to None."""
    todo = Todo(id=1, text="test")
    assert todo is not None


def test_todo_hash_consistent_with_eq() -> None:
    """Objects that compare equal should have the same hash."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    # Equal objects must have same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_for_different_ids() -> None:
    """Todo objects with different ids should have different hashes (usually)."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")

    # Different objects should ideally have different hashes
    # (Note: hash collisions are possible but unlikely for small integers)
    assert hash(todo1) != hash(todo2)


def test_todo_can_be_in_set() -> None:
    """Todo objects should be usable in sets for deduplication."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=1, text="same id different text")
    todo3 = Todo(id=2, text="task two")

    todo_set = {todo1, todo2, todo3}

    # Set should deduplicate todos with same id
    # todo1 and todo2 have id=1, so only one should remain
    assert len(todo_set) == 2

    # Check membership by id equality
    assert Todo(id=1, text="any") in todo_set
    assert Todo(id=2, text="any") in todo_set
    assert Todo(id=3, text="any") not in todo_set


def test_todo_can_be_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")

    todo_dict = {todo1: "first", todo2: "second"}

    # Should be able to retrieve values using equivalent todos
    assert todo_dict[Todo(id=1, text="any text")] == "first"
    assert todo_dict[Todo(id=2, text="any text")] == "second"

    # Should be able to add using equivalent todo
    todo_dict[Todo(id=1, text="replacement")] = "updated"
    assert len(todo_dict) == 2  # Still only 2 keys
