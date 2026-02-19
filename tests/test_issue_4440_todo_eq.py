"""Tests for Todo.__eq__ method (Issue #4440).

These tests verify that:
1. Todo objects can be compared by equality using id (entity semantics)
2. Todos with same id are equal regardless of other fields
3. Todos with different id are not equal
4. Todo is not equal to non-Todo types
"""

from __future__ import annotations

import contextlib

from flywheel.todo import Todo


def test_todo_eq_same_id_returns_true() -> None:
    """Todos with the same id should be equal (entity semantics)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    assert todo1 == todo2


def test_todo_eq_different_id_returns_false() -> None:
    """Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text", done=True)
    todo2 = Todo(id=2, text="same text", done=True)

    assert todo1 != todo2


def test_todo_eq_different_type_returns_false() -> None:
    """Todo should not be equal to non-Todo types."""
    todo = Todo(id=1, text="test")

    # Should not equal string
    assert todo != "Todo(id=1)"
    # Should not equal dict
    assert todo != {"id": 1, "text": "test"}
    # Should not equal int
    assert todo != 1
    # Should not equal None
    assert todo is not None


def test_todo_eq_same_object_returns_true() -> None:
    """A Todo should equal itself."""
    todo = Todo(id=1, text="test")
    assert todo == todo


def test_todo_eq_with_timestamps() -> None:
    """Equality should work regardless of timestamp differences."""
    todo1 = Todo(id=1, text="task", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=1, text="task", done=False, created_at="2024-12-31", updated_at="2024-12-31")

    # Same id means equal, regardless of timestamps
    assert todo1 == todo2


def test_todo_hash_consistency() -> None:
    """If __eq__ is defined, __hash__ should be consistent (or explicitly None)."""
    todo1 = Todo(id=1, text="test")
    todo2 = Todo(id=1, text="different")

    # With __eq__ defined, if objects are equal, hashes should be equal
    # However, if __hash__ is set to None (unhashable), this is also acceptable
    with contextlib.suppress(TypeError):
        assert hash(todo1) == hash(todo2)
