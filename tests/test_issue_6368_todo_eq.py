"""Tests for Todo.__eq__ method (Issue #6368).

These tests verify that:
1. Todo objects with same (id, text, done) are equal
2. Todo objects with different fields are not equal
3. Timestamps (created_at, updated_at) are not part of equality
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_business_fields() -> None:
    """Two Todo objects with same (id, text, done) should be equal."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="a", done=False)
    assert t1 == t2


def test_todo_eq_with_explicit_timestamps() -> None:
    """Timestamps should not affect equality."""
    t1 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    t2 = Todo(id=1, text="a", done=False, created_at="2025-12-31", updated_at="2025-12-31")
    assert t1 == t2


def test_todo_neq_different_id() -> None:
    """Todo objects with different ids should not be equal."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=2, text="a", done=False)
    assert t1 != t2


def test_todo_neq_different_text() -> None:
    """Todo objects with different text should not be equal."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="b", done=False)
    assert t1 != t2


def test_todo_neq_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="a", done=True)
    assert t1 != t2


def test_todo_neq_different_type() -> None:
    """Todo should not be equal to non-Todo objects."""
    t1 = Todo(id=1, text="a", done=False)
    assert t1 != "Todo(id=1, text='a', done=False)"
    assert t1 != {"id": 1, "text": "a", "done": False}
    assert t1 is not None
    assert t1 != 1


def test_todo_eq_reflexive() -> None:
    """A Todo should equal itself."""
    t1 = Todo(id=1, text="a", done=False)
    assert t1 == t1


def test_todo_eq_symmetric() -> None:
    """Equality should be symmetric."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="a", done=False)
    assert t1 == t2
    assert t2 == t1


def test_todo_eq_transitive() -> None:
    """Equality should be transitive."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="a", done=False)
    t3 = Todo(id=1, text="a", done=False)
    assert t1 == t2
    assert t2 == t3
    assert t1 == t3


def test_todo_hash_consistency() -> None:
    """Equal Todo objects should have the same hash."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="a", done=False)
    # Since __eq__ is defined with a custom __hash__, hash should work consistently
    assert hash(t1) == hash(t2)
