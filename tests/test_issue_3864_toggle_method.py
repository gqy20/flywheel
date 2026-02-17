"""Tests for Todo.toggle() method (Issue #3864).

These tests verify that:
1. Todo.toggle() flips done status from True to False or vice versa
2. updated_at is updated on toggle
3. toggle() returns new done status for convenience
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_flips_false_to_true() -> None:
    """toggle() should flip done from False to True."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = todo.toggle()

    assert todo.done is True
    assert result is True


def test_toggle_flips_true_to_false() -> None:
    """toggle() should flip done from True to False."""
    todo = Todo(id=1, text="buy milk", done=True)
    result = todo.toggle()

    assert todo.done is False
    assert result is False


def test_toggle_updates_updated_at() -> None:
    """toggle() should update the updated_at timestamp."""
    todo = Todo(id=1, text="buy milk", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)
    todo.toggle()

    assert todo.updated_at != original_updated_at


def test_toggle_multiple_times() -> None:
    """toggle() should work correctly when called multiple times."""
    todo = Todo(id=1, text="buy milk", done=False)

    # First toggle: False -> True
    todo.toggle()
    assert todo.done is True

    # Second toggle: True -> False
    todo.toggle()
    assert todo.done is False

    # Third toggle: False -> True
    todo.toggle()
    assert todo.done is True


def test_toggle_returns_new_status() -> None:
    """toggle() should return the new done status for convenience."""
    todo = Todo(id=1, text="buy milk", done=False)

    # Toggle returns new status
    result1 = todo.toggle()
    assert result1 is True

    result2 = todo.toggle()
    assert result2 is False
