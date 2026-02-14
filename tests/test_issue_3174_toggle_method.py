"""Tests for issue #3174: toggle() method for Todo class."""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_from_undone_to_done() -> None:
    """toggle() should change done=False to done=True."""
    todo = Todo(id=1, text="test todo", done=False)
    assert todo.done is False

    todo.toggle()

    assert todo.done is True


def test_toggle_from_done_to_undone() -> None:
    """toggle() should change done=True to done=False."""
    todo = Todo(id=1, text="test todo", done=True)
    assert todo.done is True

    todo.toggle()

    assert todo.done is False


def test_toggle_updates_timestamp() -> None:
    """toggle() should update updated_at timestamp."""
    todo = Todo(id=1, text="test todo", done=False)
    original_updated_at = todo.updated_at

    todo.toggle()

    assert todo.updated_at > original_updated_at


def test_toggle_returns_none() -> None:
    """toggle() should return None to match mark_done/undone style."""
    todo = Todo(id=1, text="test todo", done=False)

    result = todo.toggle()

    assert result is None


def test_multiple_toggles() -> None:
    """toggle() should work correctly when called multiple times."""
    todo = Todo(id=1, text="test todo", done=False)

    # First toggle: False -> True
    todo.toggle()
    assert todo.done is True

    # Second toggle: True -> False
    todo.toggle()
    assert todo.done is False

    # Third toggle: False -> True
    todo.toggle()
    assert todo.done is True
