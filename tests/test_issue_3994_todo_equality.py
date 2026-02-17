"""Tests for Todo.__eq__ method (Issue #3994).

These tests verify that:
1. Todo objects with same id, text, and done are semantically equal
2. Todo objects with different id, text, or done are not equal
3. Comparing Todo to non-Todo returns NotImplemented (via !=)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_equality_same_id_and_text_returns_true() -> None:
    """Two todos with same id, text, and done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_equality_different_id_returns_false() -> None:
    """Two todos with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_equality_different_text_returns_false() -> None:
    """Two todos with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy eggs", done=False)

    assert todo1 != todo2


def test_equality_different_done_returns_false() -> None:
    """Two todos with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_equality_with_non_todo_returns_notimplemented() -> None:
    """Comparing Todo to non-Todo should return NotImplemented via !=.

    The comparison should evaluate to True for != (not equal).
    """
    todo = Todo(id=1, text="buy milk", done=False)

    # Comparing Todo to non-Todo should use != and return True
    assert todo != "not a todo"
    assert todo != 1
    assert todo is not None
    assert todo != {"id": 1, "text": "buy milk", "done": False}


def test_equality_ignores_timestamps() -> None:
    """Equality comparison should ignore timestamps (created_at, updated_at)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    # Manually set different timestamps
    todo1.created_at = "2024-01-01T00:00:00+00:00"
    todo1.updated_at = "2024-01-01T00:00:00+00:00"
    todo2.created_at = "2025-01-01T00:00:00+00:00"
    todo2.updated_at = "2025-01-01T00:00:00+00:00"

    # Should still be equal despite different timestamps
    assert todo1 == todo2


def test_equality_reflexive() -> None:
    """A todo should equal itself."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert todo == todo


def test_equality_symmetric() -> None:
    """Equality should be symmetric (a == b implies b == a)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo1
