"""Tests for issue #6245: Add toggle() method to switch done state."""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_on_undone_todo_marks_it_done() -> None:
    """toggle() on undone todo marks it done."""
    todo = Todo(id=1, text="test task")
    assert todo.done is False

    result = todo.toggle()

    assert todo.done is True
    assert result is todo  # Returns self for chaining


def test_toggle_on_done_todo_marks_it_undone() -> None:
    """toggle() on done todo marks it undone."""
    todo = Todo(id=1, text="test task", done=True)
    assert todo.done is True

    result = todo.toggle()

    assert todo.done is False
    assert result is todo  # Returns self for chaining


def test_toggle_twice_returns_to_original_state() -> None:
    """Test todo.toggle().toggle() returns to original state."""
    todo = Todo(id=1, text="test task")
    assert todo.done is False

    todo.toggle()
    assert todo.done is True

    todo.toggle()
    assert todo.done is False


def test_toggle_updates_updated_at_timestamp() -> None:
    """Test updated_at is modified after toggle."""
    todo = Todo(id=1, text="test task")
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.toggle()

    assert todo.updated_at > original_updated_at


def test_toggle_supports_method_chaining() -> None:
    """toggle() returns the Todo for chaining."""
    todo = Todo(id=1, text="test task")

    # Should be able to chain multiple operations
    result = todo.toggle().toggle()

    assert result is todo
    assert todo.done is False  # Back to original state
