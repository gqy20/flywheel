"""Tests for Todo.__eq__ method (Issue #4175).

These tests verify that:
1. Todo objects with same id, text, done are equal
2. Todo objects with different id, text, or done are not equal
3. Equality comparison uses value equality, not object identity
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_values() -> None:
    """Todo objects with identical id, text, done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_todo_equality_default_done() -> None:
    """Todo equality should work with default done value."""
    todo1 = Todo(id=1, text="test")
    todo2 = Todo(id=1, text="test")

    assert todo1 == todo2


def test_todo_inequality_different_id() -> None:
    """Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")

    assert todo1 != todo2


def test_todo_inequality_different_text() -> None:
    """Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")

    assert todo1 != todo2


def test_todo_inequality_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_todo_equality_ignores_timestamps() -> None:
    """Equality should compare only id, text, done (not timestamps)."""
    todo1 = Todo(id=1, text="task")
    todo2 = Todo(id=1, text="task")

    # Even though timestamps might differ, todos should be equal
    assert todo1 == todo2


def test_todo_equality_with_other_types() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="test")

    assert todo != "Todo(id=1, text='test', done=False)"
    assert todo != {"id": 1, "text": "test", "done": False}
    assert todo != 1
    assert todo is not None


def test_todo_equality_reflexive() -> None:
    """A Todo should be equal to itself (reflexivity)."""
    todo = Todo(id=1, text="test")
    assert todo == todo


def test_todo_equality_symmetric() -> None:
    """Todo equality should be symmetric (a == b implies b == a)."""
    todo1 = Todo(id=1, text="test")
    todo2 = Todo(id=1, text="test")

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_equality_transitive() -> None:
    """Todo equality should be transitive (a == b and b == c implies a == c)."""
    todo1 = Todo(id=1, text="test")
    todo2 = Todo(id=1, text="test")
    todo3 = Todo(id=1, text="test")

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3
