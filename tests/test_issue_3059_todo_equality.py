"""Tests for Todo.__eq__ method (Issue #3059).

These tests verify that:
1. Todo objects with identical id, text, done compare equal
2. Todo objects with different fields compare unequal
3. Equality is value-based, not identity-based
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


def test_todo_equality_not_identity_based() -> None:
    """Equality should be value-based, not identity-based.

    Two different Todo instances with same values should be equal,
    even though they are different objects in memory.
    """
    todo1 = Todo(id=1, text="task a", done=False)
    todo2 = Todo(id=1, text="task a", done=False)

    # They are different objects (different identity)
    assert todo1 is not todo2
    # But they should be equal by value
    assert todo1 == todo2


def test_todo_equality_minimal_fields() -> None:
    """Todo equality should work with only required fields."""
    todo1 = Todo(id=42, text="minimal")
    todo2 = Todo(id=42, text="minimal")

    assert todo1 == todo2


def test_todo_equality_with_other_type() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk")

    assert todo != "Todo(id=1, text='buy milk')"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk"}
