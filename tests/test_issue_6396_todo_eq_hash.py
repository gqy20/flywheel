"""Tests for Todo.__eq__ and __hash__ methods (Issue #6396).

These tests verify that:
1. Todo objects can be compared for equality based on (id, text, done)
2. Todo objects can be used in sets and as dict keys
3. Todo objects with same id are deduplicated in sets
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_data() -> None:
    """Todo objects with identical data should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_todo_equality_different_id() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_equality_different_text() -> None:
    """Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_todo_equality_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_todo_hash_allows_set_usage() -> None:
    """Todo objects should be hashable and usable in sets."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    # Both todos should hash to the same value and deduplicate in a set
    todo_set = {todo1, todo2}
    assert len(todo_set) == 1


def test_todo_hash_different_ids_in_set() -> None:
    """Todo objects with different ids should both appear in a set."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    todo_set = {todo1, todo2}
    assert len(todo_set) == 2


def test_todo_hash_allows_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    todo_dict = {todo1: "first"}
    # Same todo should map to same key
    todo_dict[todo2] = "second"

    assert len(todo_dict) == 1
    assert todo_dict[todo1] == "second"


def test_todo_hash_consistency() -> None:
    """Hash should be consistent across multiple calls."""
    todo = Todo(id=1, text="buy milk", done=False)

    hash1 = hash(todo)
    hash2 = hash(todo)

    assert hash1 == hash2


def test_todo_equality_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk", "done": False}
    assert todo != None
