"""Tests for toggle_done() method - Issue #4120."""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_done_from_false_to_true() -> None:
    """Test that toggle_done() changes done from False to True."""
    todo = Todo(id=1, text="test todo")
    assert todo.done is False

    todo.toggle_done()
    assert todo.done is True


def test_toggle_done_from_true_to_false() -> None:
    """Test that toggle_done() changes done from True to False."""
    todo = Todo(id=1, text="test todo", done=True)
    assert todo.done is True

    todo.toggle_done()
    assert todo.done is False


def test_toggle_done_updates_timestamp() -> None:
    """Test that toggle_done() updates the updated_at timestamp."""
    todo = Todo(id=1, text="test todo")
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.001)

    todo.toggle_done()
    assert todo.updated_at > original_updated_at
