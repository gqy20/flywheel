"""Tests for issue #6043: toggle() method to flip done state."""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_on_undone_todo_sets_done_true() -> None:
    """Toggle on an undone todo should set done=True."""
    todo = Todo(id=1, text="test todo")
    assert todo.done is False

    todo.toggle()

    assert todo.done is True


def test_toggle_on_done_todo_sets_done_false() -> None:
    """Toggle on a done todo should set done=False."""
    todo = Todo(id=1, text="test todo", done=True)
    assert todo.done is True

    todo.toggle()

    assert todo.done is False


def test_toggle_updates_updated_at_timestamp() -> None:
    """Toggle should update the updated_at timestamp."""
    todo = Todo(id=1, text="test todo")
    original_updated_at = todo.updated_at

    todo.toggle()

    assert todo.updated_at >= original_updated_at


def test_toggle_returns_none() -> None:
    """Toggle should return None (consistent with mark_done/mark_undone)."""
    todo = Todo(id=1, text="test todo")

    result = todo.toggle()

    assert result is None


def test_toggle_can_flip_multiple_times() -> None:
    """Toggle can be called multiple times to flip state."""
    todo = Todo(id=1, text="test todo")
    assert todo.done is False

    todo.toggle()
    assert todo.done is True

    todo.toggle()
    assert todo.done is False

    todo.toggle()
    assert todo.done is True
