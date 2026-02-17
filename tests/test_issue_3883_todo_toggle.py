"""Tests for Todo.toggle() method (Issue #3883).

These tests verify that:
1. toggle() switches done=False to done=True
2. toggle() switches done=True to done=False
3. toggle() updates updated_at timestamp
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_from_undone_to_done() -> None:
    """toggle() should switch done=False to done=True."""
    todo = Todo(id=1, text="test task", done=False)
    todo.toggle()

    assert todo.done is True


def test_toggle_from_done_to_undone() -> None:
    """toggle() should switch done=True to done=False."""
    todo = Todo(id=1, text="completed task", done=True)
    todo.toggle()

    assert todo.done is False


def test_toggle_updates_updated_at_timestamp() -> None:
    """toggle() should update updated_at to current time."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.toggle()

    assert todo.updated_at != original_updated_at


def test_toggle_can_be_called_multiple_times() -> None:
    """toggle() should work correctly when called multiple times."""
    todo = Todo(id=1, text="test task", done=False)

    # Toggle multiple times
    todo.toggle()
    assert todo.done is True

    todo.toggle()
    assert todo.done is False

    todo.toggle()
    assert todo.done is True
