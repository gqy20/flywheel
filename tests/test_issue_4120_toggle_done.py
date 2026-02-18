"""Tests for toggle_done() method on Todo class.

Issue #4120: Add toggle_done() method to invert done status.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_done_from_false_to_true() -> None:
    """Toggle should change done from False to True."""
    todo = Todo(id=1, text="test todo")
    assert todo.done is False

    todo.toggle_done()

    assert todo.done is True


def test_toggle_done_from_true_to_false() -> None:
    """Toggle should change done from True to False."""
    todo = Todo(id=1, text="test todo", done=True)
    assert todo.done is True

    todo.toggle_done()

    assert todo.done is False


def test_toggle_done_updates_timestamp() -> None:
    """Toggle should update the updated_at timestamp."""
    todo = Todo(id=1, text="test todo")
    original_updated_at = todo.updated_at

    todo.toggle_done()

    assert todo.updated_at >= original_updated_at
