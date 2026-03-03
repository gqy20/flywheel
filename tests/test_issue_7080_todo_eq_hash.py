"""Tests for Todo.__eq__ and __hash__ methods (Issue #7080).

These tests verify that:
1. Todo objects with the same id are equal regardless of other fields
2. Todo objects can be hashed based on id for use in sets and dicts
3. Todo instances can be deduplicated by id in collections
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_different_text() -> None:
    """Todo objects with same id should be equal regardless of text."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    assert todo1 == todo2


def test_todo_eq_same_id_different_done() -> None:
    """Todo objects with same id should be equal regardless of done status."""
    todo1 = Todo(id=1, text="task", done=False)
    todo2 = Todo(id=1, text="task", done=True)
    assert todo1 == todo2


def test_todo_neq_different_id() -> None:
    """Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    assert todo1 != todo2


def test_todo_hash_same_id() -> None:
    """Todo objects with same id should have same hash."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_id() -> None:
    """Todo objects with different id should (usually) have different hash."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    # Hash collisions are possible but unlikely for consecutive integers
    assert hash(todo1) != hash(todo2)


def test_todo_set_deduplication() -> None:
    """Todo instances should be deduplicated by id in a set."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    todo3 = Todo(id=2, text="c")

    unique_todos = {todo1, todo2, todo3}
    assert len(unique_todos) == 2


def test_todo_dict_key() -> None:
    """Todo instances should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    mapping = {todo1: "first"}
    # Same id should map to same entry
    mapping[todo2] = "second"

    assert len(mapping) == 1
    assert mapping[todo1] == "second"


def test_todo_eq_with_non_todo() -> None:
    """Todo comparison with non-Todo should return NotImplemented/False."""
    todo = Todo(id=1, text="a")
    # Comparing with non-Todo should not raise and should return False
    assert todo != 1
    assert todo != "1"
    assert todo != {"id": 1, "text": "a"}
    assert todo != object()
