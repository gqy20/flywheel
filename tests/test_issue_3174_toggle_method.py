"""Tests for Todo.toggle() method (Issue #3174).

These tests verify that:
1. toggle() changes done=False to done=True
2. toggle() changes done=True to done=False
3. toggle() updates updated_at timestamp
4. toggle() returns None (consistent with mark_done/mark_undone)
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_from_false_to_true() -> None:
    """toggle() should change done=False to done=True."""
    todo = Todo(id=1, text="test task", done=False)
    todo.toggle()

    assert todo.done is True


def test_toggle_from_true_to_false() -> None:
    """toggle() should change done=True to done=False."""
    todo = Todo(id=1, text="completed task", done=True)
    todo.toggle()

    assert todo.done is False


def test_toggle_updates_timestamp() -> None:
    """toggle() should update updated_at timestamp."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.toggle()

    assert todo.updated_at != original_updated_at


def test_toggle_returns_none() -> None:
    """toggle() should return None for consistency with mark_done/mark_undone."""
    todo = Todo(id=1, text="test task", done=False)
    result = todo.toggle()

    assert result is None


def test_toggle_multiple_times() -> None:
    """toggle() should work correctly when called multiple times."""
    todo = Todo(id=1, text="test task", done=False)

    todo.toggle()
    assert todo.done is True

    todo.toggle()
    assert todo.done is False

    todo.toggle()
    assert todo.done is True
