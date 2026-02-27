"""Tests for issue #6146: Add toggle() method to flip done status."""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_flips_false_to_true() -> None:
    """toggle() should flip done from False to True."""
    todo = Todo(id=1, text="test task", done=False)
    todo.toggle()
    assert todo.done is True


def test_toggle_flips_true_to_false() -> None:
    """toggle() should flip done from True to False."""
    todo = Todo(id=1, text="test task", done=True)
    todo.toggle()
    assert todo.done is False


def test_toggle_updates_timestamp() -> None:
    """toggle() should update updated_at timestamp."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at
    # Small delay to ensure timestamp changes
    time.sleep(0.001)
    todo.toggle()
    assert todo.updated_at > original_updated_at


def test_toggle_returns_self_for_chaining() -> None:
    """toggle() should return self for method chaining."""
    todo = Todo(id=1, text="test task", done=False)
    result = todo.toggle()
    assert result is todo


def test_multiple_toggles() -> None:
    """Multiple toggle() calls should work correctly."""
    todo = Todo(id=1, text="test task", done=False)
    assert todo.done is False

    todo.toggle()
    assert todo.done is True

    todo.toggle()
    assert todo.done is False

    todo.toggle()
    assert todo.done is True
