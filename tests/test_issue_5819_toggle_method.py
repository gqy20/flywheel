"""Tests for issue #5819: toggle() method to flip done state."""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_from_undone_to_done() -> None:
    """toggle() should set done=True when current state is False."""
    todo = Todo(id=1, text="a", done=False)
    original_updated_at = todo.updated_at

    todo.toggle()

    assert todo.done is True
    assert todo.updated_at >= original_updated_at


def test_toggle_from_done_to_undone() -> None:
    """toggle() should set done=False when current state is True."""
    todo = Todo(id=1, text="a", done=True)
    original_updated_at = todo.updated_at

    todo.toggle()

    assert todo.done is False
    assert todo.updated_at >= original_updated_at


def test_toggle_multiple_times() -> None:
    """toggle() should work correctly when called multiple times."""
    todo = Todo(id=1, text="a", done=False)

    # First toggle: False -> True
    todo.toggle()
    assert todo.done is True

    # Second toggle: True -> False
    todo.toggle()
    assert todo.done is False

    # Third toggle: False -> True
    todo.toggle()
    assert todo.done is True
