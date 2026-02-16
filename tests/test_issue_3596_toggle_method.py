"""Tests for Todo.toggle() method (Issue #3596).

These tests verify that:
1. Calling toggle() on undone todo sets done=True
2. Calling toggle() on done todo sets done=False
3. updated_at is updated on each toggle
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_sets_undone_to_done() -> None:
    """toggle() should set done=True when starting from done=False."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp changes
    time.sleep(0.01)

    todo.toggle()

    assert todo.done is True
    assert todo.updated_at > original_updated_at


def test_toggle_sets_done_to_undone() -> None:
    """toggle() should set done=False when starting from done=True."""
    todo = Todo(id=1, text="test task", done=True)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp changes
    time.sleep(0.01)

    todo.toggle()

    assert todo.done is False
    assert todo.updated_at > original_updated_at


def test_toggle_can_flip_multiple_times() -> None:
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
