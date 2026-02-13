"""Tests for Todo.__eq__ and __hash__ methods (Issue #3030).

These tests verify that:
1. Todo objects with the same id are equal (__eq__)
2. Todo objects with different ids are not equal
3. Todo objects can be used in sets (__hash__)
4. Todo objects can be used as dictionary keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_equal() -> None:
    """Todo objects with same id should be equal."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="different text")

    assert todo1 == todo2


def test_todo_eq_different_id_not_equal() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")

    assert todo1 != todo2


def test_todo_eq_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task")

    assert todo != 1
    assert todo != "task"
    assert todo != {"id": 1, "text": "task"}
    assert todo is not None


def test_todo_hash_enables_set_deduplication() -> None:
    """Todo objects with same id should hash to same value for set deduplication."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="different text")
    todo3 = Todo(id=2, text="another task")

    # Set should deduplicate based on id
    todo_set = {todo1, todo2, todo3}
    assert len(todo_set) == 2, f"Expected 2 unique todos, got {len(todo_set)}"


def test_todo_hash_enables_dict_keys() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")  # Same id as todo1
    todo3 = Todo(id=2, text="third")

    d = {todo1: "value1", todo2: "value2", todo3: "value3"}

    # Should have 2 entries (todo1 and todo2 share same hash/id)
    assert len(d) == 2, f"Expected 2 dict entries, got {len(d)}"


def test_todo_hash_consistency() -> None:
    """Todo hash should be consistent with equality."""
    todo1 = Todo(id=1, text="text")
    todo2 = Todo(id=1, text="different text")

    # Equal objects must have same hash
    if todo1 == todo2:
        assert hash(todo1) == hash(todo2), "Equal objects must have same hash"
