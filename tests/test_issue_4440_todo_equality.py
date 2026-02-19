"""Tests for Todo.__eq__ method (Issue #4440).

These tests verify that:
1. Todo objects compare equal when they have the same id
2. Todo objects compare not equal when they have different ids
3. Todo objects compare not equal to non-Todo objects
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_returns_true() -> None:
    """Two Todo objects with the same id should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)

    assert todo1 == todo2


def test_todo_eq_different_id_returns_false() -> None:
    """Two Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_eq_different_type_returns_false() -> None:
    """A Todo should not be equal to a non-Todo object."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk", "done": False}
    assert todo is not None


def test_todo_eq_reflexive() -> None:
    """A Todo should be equal to itself."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo == todo


def test_todo_eq_symmetric() -> None:
    """Equality should be symmetric: a == b implies b == a."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")

    assert todo1 == todo2
    assert todo2 == todo1
