"""Tests for Todo equality comparison support (Issue #3366).

These tests verify that:
1. Todo objects support value-based equality comparison
2. Todos with same id/text/done compare as equal
3. Todos with different fields compare as not equal
4. Todo objects can be used in sets (hashable)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_values() -> None:
    """Two Todos with same id, text, and done should be equal (timestamps ignored)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2, "Todos with identical id/text/done should be equal (ignoring timestamps)"


def test_todo_equality_different_id() -> None:
    """Todos with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_equality_different_text() -> None:
    """Todos with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2, "Todos with different text should not be equal"


def test_todo_equality_different_done() -> None:
    """Todos with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2, "Todos with different done status should not be equal"


def test_todo_hashable_for_set() -> None:
    """Todo objects should be usable in sets via id-based hash."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    # Both should be considered the same in a set
    todo_set = {todo1, todo2}
    assert len(todo_set) == 1, "Set should deduplicate equal Todo objects"


def test_todo_equality_with_different_types() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "Todo(id=1, text='buy milk', done=False)", "Todo should not equal string"
    assert todo != {"id": 1, "text": "buy milk", "done": False}, "Todo should not equal dict"
    assert todo != 1, "Todo should not equal int"
