"""Regression tests for Issue #6043: Add toggle() method to flip done state.

This test file ensures that the Todo.toggle() method correctly flips the done
state and updates the updated_at timestamp.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_flips_undone_to_done() -> None:
    """toggle() should flip done from False to True."""
    todo = Todo(id=1, text="test todo")
    assert todo.done is False

    todo.toggle()

    assert todo.done is True


def test_toggle_flips_done_to_undone() -> None:
    """toggle() should flip done from True to False."""
    todo = Todo(id=1, text="test todo", done=True)
    assert todo.done is True

    todo.toggle()

    assert todo.done is False


def test_toggle_updates_timestamp() -> None:
    """toggle() should update the updated_at timestamp."""
    todo = Todo(id=1, text="test todo")
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference (if needed)
    todo.toggle()

    assert todo.updated_at >= original_updated_at


def test_toggle_returns_none() -> None:
    """toggle() should return None for consistency with mark_done/mark_undone."""
    todo = Todo(id=1, text="test todo")

    result = todo.toggle()

    assert result is None


def test_toggle_multiple_times() -> None:
    """toggle() should work correctly when called multiple times."""
    todo = Todo(id=1, text="test todo")

    # Start undone
    assert todo.done is False

    # Toggle to done
    todo.toggle()
    assert todo.done is True

    # Toggle back to undone
    todo.toggle()
    assert todo.done is False

    # Toggle to done again
    todo.toggle()
    assert todo.done is True
