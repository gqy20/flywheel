"""Tests for issue #4092: Add toggle method to switch completion status."""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_changes_done_from_false_to_true() -> None:
    """Issue #4092: toggle() should change done from False to True."""
    todo = Todo(id=1, text="test task", done=False)
    todo.toggle()
    assert todo.done is True


def test_toggle_changes_done_from_true_to_false() -> None:
    """Issue #4092: toggle() should change done from True to False."""
    todo = Todo(id=1, text="test task", done=True)
    todo.toggle()
    assert todo.done is False


def test_toggle_updates_updated_at() -> None:
    """Issue #4092: toggle() should update updated_at to current time."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.toggle()

    # updated_at should be different after toggle
    assert todo.updated_at != original_updated_at


def test_toggle_can_be_called_multiple_times() -> None:
    """Issue #4092: toggle() can be called repeatedly to flip state."""
    todo = Todo(id=1, text="test task", done=False)

    todo.toggle()
    assert todo.done is True

    todo.toggle()
    assert todo.done is False

    todo.toggle()
    assert todo.done is True
