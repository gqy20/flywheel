"""Direct unit tests for Todo.mark_done and Todo.mark_undone methods (Issue #7134).

These tests provide direct coverage for:
1. mark_done() sets done to True and updates updated_at
2. mark_undone() sets done to False and updates updated_at
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_mark_done_sets_done_to_true() -> None:
    """mark_done() should set done attribute to True."""
    todo = Todo(id=1, text="test task", done=False)
    assert todo.done is False

    todo.mark_done()

    assert todo.done is True


def test_todo_mark_done_updates_timestamp() -> None:
    """mark_done() should update updated_at timestamp."""
    todo = Todo(id=1, text="test task")
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.001)
    todo.mark_done()

    assert todo.updated_at != original_updated_at
    assert todo.updated_at > original_updated_at


def test_todo_mark_undone_sets_done_to_false() -> None:
    """mark_undone() should set done attribute to False."""
    todo = Todo(id=1, text="test task", done=True)
    assert todo.done is True

    todo.mark_undone()

    assert todo.done is False


def test_todo_mark_undone_updates_timestamp() -> None:
    """mark_undone() should update updated_at timestamp."""
    todo = Todo(id=1, text="test task", done=True)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.001)
    todo.mark_undone()

    assert todo.updated_at != original_updated_at
    assert todo.updated_at > original_updated_at
