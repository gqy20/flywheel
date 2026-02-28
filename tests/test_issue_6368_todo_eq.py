"""Tests for Todo.__eq__ method (Issue #6368).

These tests verify that:
1. Todo objects with same business fields are equal
2. Todo objects with different id/text/done are not equal
3. Timestamps (created_at/updated_at) don't affect equality
"""
from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_with_same_fields() -> None:
    """Todo objects with same id, text, done should be equal."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="a", done=False)
    assert t1 == t2


def test_todo_eq_ignores_timestamps() -> None:
    """Todo equality should ignore created_at/updated_at fields."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="a", done=False)
    # Even though timestamps differ due to creation time
    t1.created_at = "2024-01-01T00:00:00+00:00"
    t1.updated_at = "2024-01-01T00:00:00+00:00"
    t2.created_at = "2024-12-31T23:59:59+00:00"
    t2.updated_at = "2024-12-31T23:59:59+00:00"
    assert t1 == t2


def test_todo_neq_different_id() -> None:
    """Todo objects with different id should not be equal."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=2, text="a", done=False)
    assert t1 != t2


def test_todo_neq_different_text() -> None:
    """Todo objects with different text should not be equal."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="b", done=False)
    assert t1 != t2


def test_todo_neq_different_done() -> None:
    """Todo objects with different done should not be equal."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="a", done=True)
    assert t1 != t2


def test_todo_eq_not_equal_to_other_types() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="a", done=False)
    assert todo != "Todo(id=1, text='a', done=False)"
    assert todo != {"id": 1, "text": "a", "done": False}
    assert todo != 1
    assert todo is not None
