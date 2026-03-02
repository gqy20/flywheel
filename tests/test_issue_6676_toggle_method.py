"""Tests for Todo.toggle() method (Issue #6676).

These tests verify that:
1. todo.toggle() flips done from False to True
2. todo.toggle() flips done from True to False
3. updated_at is updated after toggle
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_flips_undone_to_done() -> None:
    """toggle() should flip done from False to True."""
    todo = Todo(id=1, text="test task", done=False)
    todo.toggle()
    assert todo.done is True


def test_toggle_flips_done_to_undone() -> None:
    """toggle() should flip done from True to False."""
    todo = Todo(id=1, text="test task", done=True)
    todo.toggle()
    assert todo.done is False


def test_toggle_updates_timestamp() -> None:
    """toggle() should update updated_at timestamp."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.001)

    todo.toggle()

    assert todo.updated_at > original_updated_at


def test_toggle_multiple_times() -> None:
    """toggle() should work correctly when called multiple times."""
    todo = Todo(id=1, text="test task", done=False)

    # Toggle multiple times
    todo.toggle()
    assert todo.done is True

    todo.toggle()
    assert todo.done is False

    todo.toggle()
    assert todo.done is True
