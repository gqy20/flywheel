"""Tests for issue #3864: Add toggle() method to flip done status."""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_flips_done_from_false_to_true() -> None:
    """Issue #3864: toggle() should flip done status from False to True."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure updated_at changes
    time.sleep(0.01)

    result = todo.toggle()

    assert todo.done is True
    assert result is True  # Returns new done status
    assert todo.updated_at > original_updated_at


def test_toggle_flips_done_from_true_to_false() -> None:
    """Issue #3864: toggle() should flip done status from True to False."""
    todo = Todo(id=1, text="test task", done=True)
    original_updated_at = todo.updated_at

    # Small delay to ensure updated_at changes
    time.sleep(0.01)

    result = todo.toggle()

    assert todo.done is False
    assert result is False  # Returns new done status
    assert todo.updated_at > original_updated_at


def test_toggle_can_be_called_multiple_times() -> None:
    """Issue #3864: toggle() should work when called multiple times."""
    todo = Todo(id=1, text="test task", done=False)

    # Toggle multiple times
    assert todo.toggle() is True  # False -> True
    assert todo.done is True

    assert todo.toggle() is False  # True -> False
    assert todo.done is False

    assert todo.toggle() is True  # False -> True again
    assert todo.done is True
