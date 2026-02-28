"""Tests for Todo.__eq__ and __hash__ methods (Issue #6244).

These tests verify that:
1. Todo objects with same id, text, done compare equal
2. Todo objects with different fields compare unequal
3. Todo objects can be added to sets and deduplicated
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_values() -> None:
    """Two Todo objects with same id, text, done should compare equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_eq_with_defaults() -> None:
    """Two Todo objects with same id and text should compare equal regardless of done default."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")

    assert todo1 == todo2


def test_todo_eq_different_id() -> None:
    """Todo objects with different ids should compare unequal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=2, text="a", done=False)

    assert todo1 != todo2


def test_todo_eq_different_text() -> None:
    """Todo objects with different text should compare unequal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="b", done=False)

    assert todo1 != todo2


def test_todo_eq_different_done() -> None:
    """Todo objects with different done status should compare unequal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=True)

    assert todo1 != todo2


def test_todo_hash_same_id_text_done() -> None:
    """Todo objects with same id, text, done should have same hash."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert hash(todo1) == hash(todo2)


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be addable to a set without error."""
    todo1 = Todo(id=1, text="a", done=False)

    # This should not raise TypeError
    todo_set = {todo1}
    assert len(todo_set) == 1
    assert todo1 in todo_set


def test_todo_set_deduplication() -> None:
    """Todo objects with same id, text, done should be deduplicated in a set."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=False)

    todo_set = {todo1, todo2}
    assert len(todo_set) == 1


def test_todo_set_keeps_different_todos() -> None:
    """Todo objects with different ids should both be kept in a set."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=2, text="b", done=True)

    todo_set = {todo1, todo2}
    assert len(todo_set) == 2


def test_todo_not_equal_to_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="a", done=False)

    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "a", "done": False}
    assert todo is not None
