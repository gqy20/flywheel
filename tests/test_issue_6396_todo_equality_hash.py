"""Tests for Todo.__eq__ and __hash__ methods (Issue #6396).

These tests verify that:
1. Todo objects can be compared for equality based on (id, text, done)
2. Todo objects can be used in sets for deduplication
3. Todo objects can be used as dictionary keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_data() -> None:
    """Two Todo objects with identical (id, text, done) should be equal."""
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


def test_todo_hash_based_on_id() -> None:
    """Todo objects with same id should have same hash."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    assert hash(todo1) == hash(todo2)


def test_todo_set_deduplication() -> None:
    """Todo objects with same id should be deduplicated in a set."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    todo_set = {todo1, todo2}
    assert len(todo_set) == 1


def test_todo_set_multiple_unique() -> None:
    """Different Todo objects should remain separate in a set."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy bread", done=False)
    todo_set = {todo1, todo2}
    assert len(todo_set) == 2


def test_todo_dict_key() -> None:
    """Todo objects can be used as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    todo_dict = {todo1: "value1"}
    # Same todo should map to same key
    assert todo_dict[todo2] == "value1"
