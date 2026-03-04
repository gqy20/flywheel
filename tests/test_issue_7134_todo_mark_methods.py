"""Tests for Todo.mark_done and mark_undone methods (Issue #7134).

These tests verify that:
1. mark_done() sets done=True and updates updated_at
2. mark_undone() sets done=False and updates updated_at
3. updated_at timestamp changes after method calls
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_mark_done() -> None:
    """mark_done() should set done=True."""
    todo = Todo(id=1, text="test task", done=False)
    assert todo.done is False

    todo.mark_done()

    assert todo.done is True


def test_todo_mark_undone() -> None:
    """mark_undone() should set done=False."""
    todo = Todo(id=1, text="test task", done=True)
    assert todo.done is True

    todo.mark_undone()

    assert todo.done is False


def test_todo_mark_done_updates_timestamp() -> None:
    """mark_done() should update the updated_at timestamp."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.mark_done()

    assert todo.updated_at != original_updated_at


def test_todo_mark_undone_updates_timestamp() -> None:
    """mark_undone() should update the updated_at timestamp."""
    todo = Todo(id=1, text="test task", done=True)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.mark_undone()

    assert todo.updated_at != original_updated_at


def test_todo_mark_done_idempotent() -> None:
    """Calling mark_done() on an already-done todo should still update timestamp."""
    todo = Todo(id=1, text="test task", done=True)
    original_updated_at = todo.updated_at

    time.sleep(0.01)

    todo.mark_done()

    assert todo.done is True
    assert todo.updated_at != original_updated_at


def test_todo_mark_undone_idempotent() -> None:
    """Calling mark_undone() on an already-undone todo should still update timestamp."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at

    time.sleep(0.01)

    todo.mark_undone()

    assert todo.done is False
    assert todo.updated_at != original_updated_at
