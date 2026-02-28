"""Tests for Todo.toggle() method (Issue #6245).

These tests verify that:
1. toggle() on undone todo marks it done
2. toggle() on done todo marks it undone
3. toggle() updates updated_at timestamp
4. toggle() returns the Todo for chaining
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_marks_undone_todo_as_done() -> None:
    """toggle() on undone todo marks it done."""
    todo = Todo(id=1, text="test task", done=False)
    todo.toggle()

    assert todo.done is True


def test_toggle_marks_done_todo_as_undone() -> None:
    """toggle() on done todo marks it undone."""
    todo = Todo(id=1, text="test task", done=True)
    todo.toggle()

    assert todo.done is False


def test_toggle_returns_self_for_chaining() -> None:
    """toggle() returns the Todo for chaining."""
    todo = Todo(id=1, text="test task", done=False)
    result = todo.toggle()

    assert result is todo


def test_toggle_double_toggles_returns_to_original_state() -> None:
    """toggle().toggle() returns to original state."""
    todo = Todo(id=1, text="test task", done=False)
    todo.toggle().toggle()

    assert todo.done is False


def test_toggle_updates_timestamp() -> None:
    """toggle() updates updated_at timestamp."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.toggle()

    assert todo.updated_at != original_updated_at
