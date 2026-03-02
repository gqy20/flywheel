"""Tests for Todo.__eq__ method (Issue #6675).

These tests verify that:
1. Todo objects can be compared for equality
2. Equality compares id, text, and done fields
3. Timestamps (created_at, updated_at) are ignored in comparison
4. Inequality works correctly for different todos
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_identical_todos() -> None:
    """Todo objects with same id, text, and done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_todo_eq_different_id() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_eq_different_text() -> None:
    """Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_todo_eq_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_todo_eq_ignores_timestamps() -> None:
    """Equality should ignore created_at and updated_at fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo1.created_at = "2024-01-01T00:00:00+00:00"
    todo1.updated_at = "2024-01-01T00:00:00+00:00"

    todo2 = Todo(id=1, text="buy milk", done=False)
    todo2.created_at = "2024-12-31T23:59:59+00:00"
    todo2.updated_at = "2024-12-31T23:59:59+00:00"

    # Should be equal despite different timestamps
    assert todo1 == todo2


def test_todo_eq_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "buy milk"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk", "done": False}
    assert todo is not None


def test_todo_eq_reflexive() -> None:
    """A Todo should be equal to itself."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert todo == todo


def test_todo_eq_symmetric() -> None:
    """Equality should be symmetric: if a == b then b == a."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_eq_transitive() -> None:
    """Equality should be transitive: if a == b and b == c then a == c."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    todo3 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3
