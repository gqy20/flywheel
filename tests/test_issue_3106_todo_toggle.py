"""Tests for Todo.toggle() method (Issue #3106).

These tests verify that:
1. Todo.toggle() method exists and flips done state
2. toggle() updates updated_at timestamp
3. toggle() returns the new done state for convenience
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_on_undone_todo_sets_done_true() -> None:
    """toggle() on an undone todo should set done=True."""
    todo = Todo(id=1, text="test task", done=False)
    result = todo.toggle()

    assert todo.done is True
    assert result is True


def test_toggle_on_done_todo_sets_done_false() -> None:
    """toggle() on a done todo should set done=False."""
    todo = Todo(id=1, text="test task", done=True)
    result = todo.toggle()

    assert todo.done is False
    assert result is False


def test_toggle_updates_updated_at_timestamp() -> None:
    """toggle() should update the updated_at timestamp."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)
    todo.toggle()

    assert todo.updated_at != original_updated_at


def test_toggle_returns_new_done_state() -> None:
    """toggle() should return the new done state for convenience."""
    todo = Todo(id=1, text="test task", done=False)

    # First toggle: False -> True, returns True
    result1 = todo.toggle()
    assert result1 is True
    assert todo.done is True

    # Second toggle: True -> False, returns False
    result2 = todo.toggle()
    assert result2 is False
    assert todo.done is False
