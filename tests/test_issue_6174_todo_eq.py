"""Tests for Todo.__eq__ method (Issue #6174).

These tests verify that:
1. Todo objects with same id/text/done are equal
2. Todo objects with different done status are not equal
3. created_at/updated_at differences do not affect equality
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_text_done() -> None:
    """Todo objects with same id, text, done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_eq_different_done_status() -> None:
    """Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2
    assert todo2 != todo1


def test_todo_eq_different_text() -> None:
    """Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_todo_eq_different_id() -> None:
    """Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_eq_ignores_timestamps() -> None:
    """Todo equality should ignore created_at/updated_at differences."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo1.created_at = "2025-01-01T00:00:00+00:00"
    todo1.updated_at = "2025-01-01T00:00:00+00:00"

    todo2 = Todo(id=1, text="buy milk", done=False)
    todo2.created_at = "2026-12-31T23:59:59+00:00"
    todo2.updated_at = "2026-12-31T23:59:59+00:00"

    # Despite different timestamps, should be equal
    assert todo1 == todo2


def test_todo_eq_with_non_todo() -> None:
    """Todo comparison with non-Todo should return NotImplemented/False."""
    todo = Todo(id=1, text="buy milk", done=False)

    # Comparing with a different type should return False
    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk", "done": False}
    assert not todo.__eq__(None)  # type: ignore[arg-type]


def test_todo_eq_explicit_method() -> None:
    """Test __eq__ method directly per issue acceptance criteria."""
    # Per issue: Todo(id=1, text='a').__eq__(Todo(id=1, text='a')) returns True
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")
    assert todo1.__eq__(todo2) is True

    # Per issue: Todo(id=1, text='a', done=False).__eq__(Todo(id=1, text='a', done=True)) returns False
    todo3 = Todo(id=1, text="a", done=False)
    todo4 = Todo(id=1, text="a", done=True)
    assert todo3.__eq__(todo4) is False
