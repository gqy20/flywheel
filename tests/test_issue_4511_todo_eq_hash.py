"""Tests for Todo.__eq__ and __hash__ methods (Issue #4511).

These tests verify that:
1. Todo objects with same fields are equal
2. Todo objects with different ids are not equal
3. Todo objects can be placed in sets or used as dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_fields() -> None:
    """Todo(id=1, text='a') == Todo(id=1, text='a') should return True."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")

    assert todo1 == todo2


def test_todo_eq_different_id() -> None:
    """Todo(id=1, text='a') != Todo(id=2, text='a') should return True."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=2, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")

    assert todo1 != todo2


def test_todo_eq_different_text() -> None:
    """Todos with different text should not be equal."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=1, text="b", done=False, created_at="2024-01-01", updated_at="2024-01-01")

    assert todo1 != todo2


def test_todo_eq_different_done() -> None:
    """Todos with different done status should not be equal."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=1, text="a", done=True, created_at="2024-01-01", updated_at="2024-01-01")

    assert todo1 != todo2


def test_todo_hash_consistent() -> None:
    """hash(Todo) should return consistent values for same todo."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")

    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_id() -> None:
    """hash(Todo) should return different values for different ids."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=2, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")

    assert hash(todo1) != hash(todo2)


def test_todo_in_set() -> None:
    """Todo objects should be placeable in a set."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo3 = Todo(id=2, text="b", done=False, created_at="2024-01-01", updated_at="2024-01-01")

    todo_set = {todo1, todo2, todo3}

    # Set should deduplicate equal todos
    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set
    assert todo3 in todo_set


def test_todo_as_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo3 = Todo(id=2, text="b", done=False, created_at="2024-01-01", updated_at="2024-01-01")

    todo_dict = {todo1: "first", todo3: "second"}

    # Equal todo should map to same key
    assert todo_dict[todo2] == "first"
    assert todo_dict[todo3] == "second"
