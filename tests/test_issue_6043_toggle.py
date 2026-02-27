"""Tests for Todo.toggle() method (Issue #6043).

These tests verify that:
1. toggle() flips done from False to True
2. toggle() flips done from True to False
3. toggle() updates updated_at timestamp
4. toggle() returns None (consistent with mark_done/mark_undone)
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_on_undone_todo_sets_done_true() -> None:
    """toggle() should flip done from False to True."""
    todo = Todo(id=1, text="test task", done=False)
    todo.toggle()

    assert todo.done is True


def test_toggle_on_done_todo_sets_done_false() -> None:
    """toggle() should flip done from True to False."""
    todo = Todo(id=1, text="test task", done=True)
    todo.toggle()

    assert todo.done is False


def test_toggle_updates_updated_at_timestamp() -> None:
    """toggle() should update updated_at timestamp."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)
    todo.toggle()

    assert todo.updated_at != original_updated_at


def test_toggle_returns_none() -> None:
    """toggle() should return None (consistent with mark_done/mark_undone)."""
    todo = Todo(id=1, text="test task", done=False)
    result = todo.toggle()

    assert result is None


def test_toggle_flips_multiple_times() -> None:
    """toggle() should work correctly when called multiple times."""
    todo = Todo(id=1, text="test task", done=False)

    # First toggle: False -> True
    todo.toggle()
    assert todo.done is True

    # Second toggle: True -> False
    todo.toggle()
    assert todo.done is False

    # Third toggle: False -> True
    todo.toggle()
    assert todo.done is True
