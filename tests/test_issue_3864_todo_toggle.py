"""Tests for Todo.toggle() method (Issue #3864).

These tests verify that:
1. Todo.toggle() flips done status from False to True and vice versa
2. updated_at is updated on toggle
3. toggle() returns the new done status for convenience
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_flips_done_from_false_to_true() -> None:
    """toggle() should flip done status from False to True."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = todo.toggle()

    assert todo.done is True
    assert result is True  # Returns new done status


def test_toggle_flips_done_from_true_to_false() -> None:
    """toggle() should flip done status from True to False."""
    todo = Todo(id=1, text="buy milk", done=True)
    result = todo.toggle()

    assert todo.done is False
    assert result is False  # Returns new done status


def test_toggle_multiple_times() -> None:
    """toggle() should work correctly when called multiple times."""
    todo = Todo(id=1, text="test task", done=False)

    # First toggle: False -> True
    assert todo.toggle() is True
    assert todo.done is True

    # Second toggle: True -> False
    assert todo.toggle() is False
    assert todo.done is False

    # Third toggle: False -> True
    assert todo.toggle() is True
    assert todo.done is True


def test_toggle_updates_updated_at() -> None:
    """toggle() should update updated_at timestamp."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp changes
    time.sleep(0.01)

    todo.toggle()

    assert todo.updated_at != original_updated_at
