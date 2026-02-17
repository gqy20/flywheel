"""Tests for Todo.__eq__ method (Issue #3994).

These tests verify that:
1. Todo objects with same id, text, and done are semantically equal
2. Todo objects with different id are not equal
3. Comparing Todo to non-Todo returns NotImplemented (which results in False)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_equality_same_id_and_text_returns_true() -> None:
    """Two Todo objects with same id, text, and done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_equality_different_id_returns_false() -> None:
    """Two Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_equality_with_non_todo_returns_notimplemented() -> None:
    """Comparing Todo to non-Todo should return NotImplemented (False)."""
    todo = Todo(id=1, text="buy milk", done=False)

    # Comparing with non-Todo should return False
    assert todo != "not a todo"
    assert todo != 1
    assert todo is not None
    assert todo != {"id": 1, "text": "buy milk", "done": False}


def test_equality_different_text_returns_false() -> None:
    """Two Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_equality_different_done_returns_false() -> None:
    """Two Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_equality_reflexive() -> None:
    """A Todo should be equal to itself."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo == todo


def test_equality_symmetric() -> None:
    """If todo1 == todo2, then todo2 == todo1."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo1


def test_equality_transitive() -> None:
    """If todo1 == todo2 and todo2 == todo3, then todo1 == todo3."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    todo3 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3
