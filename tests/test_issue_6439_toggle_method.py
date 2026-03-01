"""Tests for toggle() convenience method (Issue #6439)."""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_from_undone_to_done() -> None:
    """toggle() on undone todo returns True and sets done=True."""
    todo = Todo(id=1, text="test todo")
    assert todo.done is False

    result = todo.toggle()

    assert result is True
    assert todo.done is True


def test_toggle_from_done_to_undone() -> None:
    """toggle() on done todo returns False and sets done=False."""
    todo = Todo(id=1, text="test todo", done=True)
    assert todo.done is True

    result = todo.toggle()

    assert result is False
    assert todo.done is False


def test_toggle_updates_timestamp() -> None:
    """updated_at is updated after toggle."""
    todo = Todo(id=1, text="test todo")
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.toggle()

    assert todo.updated_at > original_updated_at


def test_toggle_multiple_times() -> None:
    """Toggle can be called multiple times to flip state back and forth."""
    todo = Todo(id=1, text="test todo")

    # Initial state: undone
    assert todo.done is False

    # First toggle: undone -> done
    assert todo.toggle() is True
    assert todo.done is True

    # Second toggle: done -> undone
    assert todo.toggle() is False
    assert todo.done is False

    # Third toggle: undone -> done
    assert todo.toggle() is True
    assert todo.done is True
