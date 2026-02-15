"""Tests for issue #3408: Add toggle method to flip done state."""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_on_undone_todo_sets_done_true() -> None:
    """Toggle on undone todo should set done=True and return True."""
    todo = Todo(id=1, text="x", done=False)
    original_updated_at = todo.updated_at

    result = todo.toggle()

    assert result is True
    assert todo.done is True
    assert todo.updated_at >= original_updated_at


def test_toggle_on_done_todo_sets_done_false() -> None:
    """Toggle on done todo should set done=False and return False."""
    todo = Todo(id=1, text="x", done=True)
    original_updated_at = todo.updated_at

    result = todo.toggle()

    assert result is False
    assert todo.done is False
    assert todo.updated_at >= original_updated_at


def test_toggle_flips_state_multiple_times() -> None:
    """Toggle should correctly flip state back and forth."""
    todo = Todo(id=1, text="x", done=False)

    # First toggle: False -> True
    assert todo.toggle() is True
    assert todo.done is True

    # Second toggle: True -> False
    assert todo.toggle() is False
    assert todo.done is False

    # Third toggle: False -> True
    assert todo.toggle() is True
    assert todo.done is True
