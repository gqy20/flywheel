"""Tests for Todo.toggle() method (Issue #3146).

These tests verify that:
1. toggle() switches done from False to True
2. toggle() switches done from True to False
3. toggle() updates the updated_at timestamp
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_toggle_from_undone_to_done() -> None:
    """toggle() should switch done from False to True."""
    todo = Todo(id=1, text="buy milk", done=False)
    todo.toggle()

    assert todo.done is True


def test_todo_toggle_from_done_to_undone() -> None:
    """toggle() should switch done from True to False."""
    todo = Todo(id=1, text="buy milk", done=True)
    todo.toggle()

    assert todo.done is False


def test_todo_toggle_updates_timestamp() -> None:
    """toggle() should update the updated_at timestamp."""
    todo = Todo(id=1, text="buy milk", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.001)

    todo.toggle()

    assert todo.updated_at != original_updated_at


def test_todo_toggle_can_be_called_multiple_times() -> None:
    """toggle() can be called multiple times to flip state."""
    todo = Todo(id=1, text="buy milk", done=False)

    todo.toggle()
    assert todo.done is True

    todo.toggle()
    assert todo.done is False

    todo.toggle()
    assert todo.done is True
