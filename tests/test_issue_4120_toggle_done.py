"""Tests for Todo.toggle_done() method (Issue #4120).

These tests verify that:
1. toggle_done() method exists on Todo class
2. toggle_done() inverts done status from False to True
3. toggle_done() inverts done status from True to False
4. toggle_done() updates updated_at timestamp
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_done_from_false_to_true() -> None:
    """toggle_done() should set done=True when called on an undone todo."""
    todo = Todo(id=1, text="test task", done=False)
    todo.toggle_done()

    assert todo.done is True


def test_toggle_done_from_true_to_false() -> None:
    """toggle_done() should set done=False when called on a completed todo."""
    todo = Todo(id=1, text="test task", done=True)
    todo.toggle_done()

    assert todo.done is False


def test_toggle_done_updates_timestamp() -> None:
    """toggle_done() should update the updated_at timestamp."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.toggle_done()

    assert todo.updated_at != original_updated_at


def test_toggle_done_double_toggle_returns_to_original() -> None:
    """Calling toggle_done() twice should return to the original state."""
    todo = Todo(id=1, text="test task", done=False)

    todo.toggle_done()
    assert todo.done is True

    todo.toggle_done()
    assert todo.done is False
