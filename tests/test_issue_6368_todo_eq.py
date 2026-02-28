"""Tests for Todo.__eq__ method (Issue #6368).

These tests verify that:
1. Todo objects with same business fields are equal
2. Timestamps (created_at/updated_at) do not affect equality
3. Different id/text/done values result in inequality
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_with_same_fields() -> None:
    """Todo objects with same id, text, done should be equal."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="a", done=False)
    assert t1 == t2


def test_todo_eq_with_different_id() -> None:
    """Todo objects with different id should not be equal."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=2, text="a", done=False)
    assert t1 != t2


def test_todo_eq_with_different_text() -> None:
    """Todo objects with different text should not be equal."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="b", done=False)
    assert t1 != t2


def test_todo_eq_with_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="a", done=True)
    assert t1 != t2


def test_todo_eq_ignores_timestamps() -> None:
    """Equality should ignore created_at and updated_at fields."""
    t1 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    t2 = Todo(id=1, text="a", done=False, created_at="2024-12-31T23:59:59+00:00", updated_at="2024-12-31T23:59:59+00:00")
    assert t1 == t2


def test_todo_eq_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="a", done=False)
    assert todo != "Todo(id=1, text='a', done=False)"
    assert todo != 1
    assert todo != {"id": 1, "text": "a", "done": False}
    assert todo is not None


def test_todo_eq_reflexive() -> None:
    """A Todo should equal itself (reflexivity)."""
    t1 = Todo(id=1, text="a", done=False)
    assert t1 == t1


def test_todo_eq_symmetric() -> None:
    """Equality should be symmetric (a == b implies b == a)."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="a", done=False)
    assert t1 == t2
    assert t2 == t1


def test_todo_eq_transitive() -> None:
    """Equality should be transitive (a == b and b == c implies a == c)."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="a", done=False)
    t3 = Todo(id=1, text="a", done=False)
    assert t1 == t2
    assert t2 == t3
    assert t1 == t3
