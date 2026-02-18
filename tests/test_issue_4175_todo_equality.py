"""Tests for Todo.__eq__ method (Issue #4175).

These tests verify that:
1. Todo objects can be compared for equality by value, not identity
2. Equality is based on id, text, and done fields (timestamps excluded)
3. Unequal values return False correctly
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_values() -> None:
    """Todo objects with same id, text, done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    assert todo1 == todo2


def test_todo_equality_different_id() -> None:
    """Todo objects with different id should not be equal."""
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


def test_todo_equality_ignores_timestamps() -> None:
    """Todo equality should ignore timestamps."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00Z", updated_at="2024-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-31T23:59:59Z", updated_at="2024-12-31T23:59:59Z")
    assert todo1 == todo2


def test_todo_equality_with_other_types() -> None:
    """Todo compared with non-Todo should return False (or NotImplemented)."""
    todo = Todo(id=1, text="buy milk", done=False)
    # Comparing with different type should not raise and should return False
    assert (todo == "not a todo") is False
    assert (todo == 1) is False
    assert (todo == None) is False  # noqa: E711
