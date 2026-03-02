"""Tests for issue #6676: Add toggle method to flip done status."""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_flips_undone_to_done() -> None:
    """Toggle on an undone todo should mark it as done."""
    todo = Todo(id=1, text="test todo", done=False)

    todo.toggle()

    assert todo.done is True


def test_toggle_flips_done_to_undone() -> None:
    """Toggle on a done todo should mark it as undone."""
    todo = Todo(id=1, text="test todo", done=True)

    todo.toggle()

    assert todo.done is False


def test_toggle_updates_updated_at() -> None:
    """Toggle should update the updated_at timestamp."""
    todo = Todo(id=1, text="test todo", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)
    todo.toggle()

    assert todo.updated_at > original_updated_at


def test_toggle_can_flip_multiple_times() -> None:
    """Toggle should work correctly when called multiple times."""
    todo = Todo(id=1, text="test todo", done=False)

    todo.toggle()
    assert todo.done is True

    todo.toggle()
    assert todo.done is False

    todo.toggle()
    assert todo.done is True
