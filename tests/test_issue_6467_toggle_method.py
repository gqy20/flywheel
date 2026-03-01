"""Regression tests for Issue #6467: Add toggle method to flip done status.

This test file ensures that the Todo.toggle() method correctly flips the done
status and updates the updated_at timestamp.
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_from_false_to_true() -> None:
    """toggle() should change done from False to True.

    When toggle() is called on a todo with done=False, it should set done=True.
    """
    todo = Todo(id=1, text="test todo", done=False)

    todo.toggle()

    assert todo.done is True


def test_toggle_from_true_to_false() -> None:
    """toggle() should change done from True to False.

    When toggle() is called on a todo with done=True, it should set done=False.
    """
    todo = Todo(id=1, text="test todo", done=True)

    todo.toggle()

    assert todo.done is False


def test_toggle_updates_timestamp() -> None:
    """toggle() should update the updated_at timestamp.

    When toggle() is called, updated_at should be refreshed to current time.
    """
    todo = Todo(id=1, text="test todo", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.toggle()

    assert todo.updated_at != original_updated_at


def test_toggle_returns_none() -> None:
    """toggle() should return None for consistency with mark_done()/mark_undone().

    The toggle() method should follow the same pattern as mark_done() and
    mark_undone() which return None.
    """
    todo = Todo(id=1, text="test todo", done=False)

    result = todo.toggle()

    assert result is None


def test_toggle_multiple_times() -> None:
    """toggle() should work correctly when called multiple times.

    Calling toggle() twice should return to the original state.
    """
    todo = Todo(id=1, text="test todo", done=False)

    todo.toggle()
    assert todo.done is True

    todo.toggle()
    assert todo.done is False

    todo.toggle()
    assert todo.done is True
