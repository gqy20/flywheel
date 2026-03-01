"""Tests for Todo.__eq__ method (Issue #6522).

These tests verify that:
1. Todo objects can be compared for equality by value
2. Equality compares id, text, and done fields (not timestamps)
3. Comparison with non-Todo types returns NotImplemented
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_values() -> None:
    """Two todos with same id, text, done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    assert todo1 == todo2


def test_todo_eq_different_id() -> None:
    """Todos with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)
    assert todo1 != todo2


def test_todo_eq_different_text() -> None:
    """Todos with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)
    assert todo1 != todo2


def test_todo_eq_different_done() -> None:
    """Todos with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)
    assert todo1 != todo2


def test_todo_eq_with_none() -> None:
    """Comparison with None should return NotImplemented (evaluates to False)."""
    todo = Todo(id=1, text="buy milk", done=False)
    # Comparing with non-Todo should return NotImplemented, which Python
    # handles by trying the reverse comparison, ultimately resulting in False
    assert todo != None  # noqa: E711


def test_todo_eq_with_other_type() -> None:
    """Comparison with non-Todo type should return NotImplemented."""
    todo = Todo(id=1, text="buy milk", done=False)
    # Comparing with a string should not raise and should return False
    assert todo != "not a todo"
    # Comparing with a dict should not raise and should return False
    assert todo != {"id": 1, "text": "buy milk", "done": False}


def test_todo_eq_excludes_timestamps() -> None:
    """Todos with same core fields but different timestamps should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    # Force different timestamps
    todo1.created_at = "2024-01-01T00:00:00+00:00"
    todo1.updated_at = "2024-01-01T00:00:00+00:00"
    todo2.created_at = "2024-12-31T23:59:59+00:00"
    todo2.updated_at = "2024-12-31T23:59:59+00:00"

    # Should still be equal because timestamps are excluded from comparison
    assert todo1 == todo2


def test_todo_eq_reflexive() -> None:
    """A todo should be equal to itself (reflexivity)."""
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
