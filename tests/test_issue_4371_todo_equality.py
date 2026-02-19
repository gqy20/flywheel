"""Tests for Todo.__eq__ method (Issue #4371).

These tests verify value-based equality comparison for Todo objects:
1. Two Todo instances with identical id, text, done compare equal
2. Two Todo instances with different any field compare unequal
3. Comparing Todo to non-Todo returns NotImplemented (False)
"""

from __future__ import annotations

import contextlib

from flywheel.todo import Todo


def test_todo_eq_same_content_equal() -> None:
    """Two Todo instances with identical id, text, done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    assert todo1 == todo2


def test_todo_eq_different_id_not_equal() -> None:
    """Two Todo instances with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)
    assert todo1 != todo2


def test_todo_eq_different_text_not_equal() -> None:
    """Two Todo instances with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)
    assert todo1 != todo2


def test_todo_eq_different_done_not_equal() -> None:
    """Two Todo instances with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=True)
    todo2 = Todo(id=1, text="buy milk", done=False)
    assert todo1 != todo2


def test_todo_eq_ignores_timestamps() -> None:
    """Equality should ignore created_at and updated_at timestamps."""
    todo1 = Todo(
        id=1,
        text="buy milk",
        done=False,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )
    todo2 = Todo(
        id=1,
        text="buy milk",
        done=False,
        created_at="2024-12-31T23:59:59",
        updated_at="2024-12-31T23:59:59",
    )
    assert todo1 == todo2


def test_todo_eq_non_todo_returns_not_implemented() -> None:
    """Comparing Todo to non-Todo should return False."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk", "done": False}
    assert todo is not None


def test_todo_eq_symmetry() -> None:
    """Equality should be symmetric (a == b implies b == a)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_eq_reflexivity() -> None:
    """A Todo should be equal to itself."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert todo == todo


def test_todo_eq_consistency_with_hash() -> None:
    """If two Todos are equal, they should have the same hash (if hashable)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    # Note: dataclasses with eq=True but no frozen=True are not hashable by default
    # This test documents the current behavior - if hashing is needed, frozen=True
    # would need to be added or a custom __hash__ implemented
    with contextlib.suppress(TypeError):
        assert hash(todo1) == hash(todo2)
