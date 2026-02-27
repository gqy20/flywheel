"""Tests for issue #6146: Add toggle() method to flip done status."""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_flips_false_to_true() -> None:
    """toggle() should flip done from False to True."""
    todo = Todo(id=1, text="test todo", done=False)
    result = todo.toggle()

    assert todo.done is True
    assert result is todo  # Returns self for method chaining


def test_toggle_flips_true_to_false() -> None:
    """toggle() should flip done from True to False."""
    todo = Todo(id=1, text="test todo", done=True)
    result = todo.toggle()

    assert todo.done is False
    assert result is todo  # Returns self for method chaining


def test_toggle_updates_updated_at_timestamp() -> None:
    """toggle() should update the updated_at timestamp."""
    todo = Todo(id=1, text="test todo", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.toggle()

    assert todo.updated_at > original_updated_at


def test_toggle_can_be_chained() -> None:
    """toggle() returns self, enabling method chaining."""
    todo = Todo(id=1, text="test todo", done=False)

    # Should be able to chain toggle calls
    result = todo.toggle().toggle()

    # Two toggles should return to original state
    assert todo.done is False
    assert result is todo
