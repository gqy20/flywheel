"""Tests for Todo.__eq__ and Todo.__hash__ methods (Issue #5930).

These tests verify that:
1. Todo equality is based only on id field
2. Todo hash is based only on id field
3. Todos with same id can be used in sets/dicts
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_based_on_id_only() -> None:
    """Todo equality should be based on id only, not other fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    # Same id means equal, even with different text and done
    assert todo1 == todo2


def test_todo_inequality_different_ids() -> None:
    """Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text", done=True)
    todo2 = Todo(id=2, text="same text", done=True)

    # Different id means not equal, even with same other fields
    assert todo1 != todo2


def test_todo_hash_based_on_id() -> None:
    """Todo hash should be based on id only for set/dict operations."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    # Same id should have same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_ids() -> None:
    """Todos with different ids should have different hashes."""
    todo1 = Todo(id=1, text="same text", done=True)
    todo2 = Todo(id=2, text="same text", done=True)

    # Different ids should have different hashes (likely, not guaranteed)
    # But at minimum they should be hashable
    assert hash(todo1) != hash(todo2)


def test_todo_set_deduplication() -> None:
    """Todos with same id should be deduplicated in a set."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)
    todo3 = Todo(id=2, text="another task", done=False)

    todo_set = {todo1, todo2, todo3}

    # Only 2 unique todos (id=1 and id=2)
    assert len(todo_set) == 2


def test_todo_dict_key_usage() -> None:
    """Todos with same id should work as dict keys."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    todo_dict = {todo1: "first"}

    # todo2 should be considered same key as todo1
    assert todo_dict[todo2] == "first"
