"""Tests for issue #7249: Add toggle() method to flip done status."""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_flips_undone_to_done() -> None:
    """toggle() on undone todo sets done=True."""
    todo = Todo(id=1, text="test", done=False)
    todo.toggle()
    assert todo.done is True


def test_toggle_flips_done_to_undone() -> None:
    """toggle() on done todo sets done=False."""
    todo = Todo(id=1, text="test", done=True)
    todo.toggle()
    assert todo.done is False


def test_toggle_updates_updated_at() -> None:
    """toggle() updates updated_at timestamp."""
    todo = Todo(id=1, text="test", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.toggle()
    assert todo.updated_at > original_updated_at
