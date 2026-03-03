"""Tests for Todo.__eq__ and __hash__ methods (Issue #7080).

These tests verify that:
1. Todo objects with the same id are equal (value-based comparison)
2. Todo objects with the same id have the same hash (for set/dict usage)
3. Todo instances can be deduplicated by id in sets
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_same_text() -> None:
    """Todo instances with same id and text should be equal."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy milk")
    assert todo1 == todo2


def test_todo_eq_same_id_different_text() -> None:
    """Todo instances with same id should be equal regardless of text."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")
    assert todo1 == todo2


def test_todo_eq_different_id() -> None:
    """Todo instances with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")
    assert todo1 != todo2


def test_todo_eq_different_done_status() -> None:
    """Todo instances with same id should be equal regardless of done status."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)
    assert todo1 == todo2


def test_todo_hash_same_id_same_text() -> None:
    """Todo instances with same id and text should have same hash."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy milk")
    assert hash(todo1) == hash(todo2)


def test_todo_hash_same_id_different_text() -> None:
    """Todo instances with same id should have same hash regardless of text."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")
    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_id() -> None:
    """Todo instances with different ids should have different hashes."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")
    # Different ids should generally have different hashes (not guaranteed but expected)
    assert hash(todo1) != hash(todo2)


def test_todo_set_deduplication() -> None:
    """Todo instances can be added to a set and deduplicated by id."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")
    todo3 = Todo(id=2, text="buy eggs")

    # Set should have 2 unique todos (by id)
    unique_todos = {todo1, todo2, todo3}
    assert len(unique_todos) == 2


def test_todo_dict_key() -> None:
    """Todo instances can be used as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")

    # Using todos as dict keys
    d = {todo1: "first"}

    # Same id should map to same key
    assert d[todo2] == "first"

    # Can update value via equivalent key
    d[todo2] = "updated"
    assert d[todo1] == "updated"
