"""Regression tests for Issue #3408: Add toggle method to flip done state.

This test file ensures that toggle() method correctly flips the done boolean
and updates the updated_at timestamp.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_on_undone_todo_sets_done_true() -> None:
    """toggle() on undone todo should set done=True and return True."""
    todo = Todo(id=1, text="test todo", done=False)
    original_updated_at = todo.updated_at

    result = todo.toggle()

    assert result is True
    assert todo.done is True
    assert todo.updated_at >= original_updated_at


def test_toggle_on_done_todo_sets_done_false() -> None:
    """toggle() on done todo should set done=False and return False."""
    todo = Todo(id=1, text="test todo", done=True)
    original_updated_at = todo.updated_at

    result = todo.toggle()

    assert result is False
    assert todo.done is False
    assert todo.updated_at >= original_updated_at


def test_toggle_returns_new_boolean_state() -> None:
    """toggle() should return the new boolean state for convenience."""
    todo = Todo(id=1, text="test todo", done=False)

    # First toggle: False -> True, should return True
    assert todo.toggle() is True
    assert todo.done is True

    # Second toggle: True -> False, should return False
    assert todo.toggle() is False
    assert todo.done is False

    # Third toggle: False -> True, should return True again
    assert todo.toggle() is True
    assert todo.done is True


def test_toggle_updates_timestamp() -> None:
    """toggle() should update updated_at timestamp."""
    todo = Todo(id=1, text="test todo", done=False)
    timestamp_before = todo.updated_at

    todo.toggle()

    # Timestamp should be updated
    assert todo.updated_at >= timestamp_before
