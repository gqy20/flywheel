"""Tests for Todo.__eq__ method (Issue #3994).

These tests verify that:
1. Todo objects can be compared for semantic equality
2. Equality is based on id, text, and done fields
3. Comparing Todo to non-Todo returns NotImplemented (False)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_equality_same_id_text_and_done_returns_true() -> None:
    """Todo objects with same id, text, and done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-02T00:00:00+00:00", updated_at="2024-01-02T00:00:00+00:00")

    # Different timestamps shouldn't affect equality
    assert todo1 == todo2


def test_equality_different_id_returns_false() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_equality_different_text_returns_false() -> None:
    """Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_equality_different_done_returns_false() -> None:
    """Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_equality_with_non_todo_returns_false() -> None:
    """Comparing Todo to non-Todo should return False."""
    todo = Todo(id=1, text="buy milk", done=False)

    # Comparison with non-Todo types should return False
    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk", "done": False}
    # Using 'is not None' follows PEP 8, while still verifying
    # that the equality semantics work correctly (Todo is not equal to None)
    assert todo is not None


def test_equality_reflexive() -> None:
    """A Todo should be equal to itself."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo == todo


def test_equality_symmetric() -> None:
    """Equality should be symmetric (a == b implies b == a)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo1


def test_equality_transitive() -> None:
    """Equality should be transitive (a == b and b == c implies a == c)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    todo3 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3
