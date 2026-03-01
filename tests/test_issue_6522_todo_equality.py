"""Tests for Todo.__eq__ method (Issue #6522).

These tests verify that:
1. Todo objects with same id, text, done are equal
2. Todo objects with different id, text, or done are not equal
3. Comparison with non-Todo objects returns NotImplemented/False
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_with_same_values() -> None:
    """Todo objects with same id, text, done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_todo_equality_with_different_id() -> None:
    """Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_equality_with_different_text() -> None:
    """Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_todo_equality_with_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_todo_equality_ignores_timestamps() -> None:
    """Todo equality should ignore timestamps (created_at, updated_at)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo1.created_at = "2024-01-01T00:00:00+00:00"
    todo1.updated_at = "2024-01-01T00:00:00+00:00"

    todo2 = Todo(id=1, text="buy milk", done=False)
    todo2.created_at = "2024-12-31T23:59:59+00:00"
    todo2.updated_at = "2024-12-31T23:59:59+00:00"

    # Should be equal despite different timestamps
    assert todo1 == todo2


def test_todo_equality_with_non_todo() -> None:
    """Comparison with non-Todo should return NotImplemented/False."""
    todo = Todo(id=1, text="buy milk", done=False)

    # Comparing with None should return False (not raise)
    assert todo != None

    # Comparing with dict should return False
    assert todo != {"id": 1, "text": "buy milk", "done": False}

    # Comparing with string should return False
    assert todo != "Todo(id=1, text='buy milk', done=False)"


def test_todo_equality_reflexive() -> None:
    """A Todo should be equal to itself."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert todo == todo


def test_todo_equality_symmetric() -> None:
    """Equality should be symmetric (a == b implies b == a)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_equality_transitive() -> None:
    """Equality should be transitive (a == b and b == c implies a == c)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    todo3 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3
