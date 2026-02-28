"""Tests for toggle() method - Issue #6245."""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_toggle_changes_done_from_false_to_true() -> None:
    """Toggle on undone todo should mark it done."""
    todo = Todo(id=1, text="test todo")
    assert todo.done is False

    result = todo.toggle()

    assert todo.done is True
    assert result is todo  # Returns self for chaining


def test_toggle_changes_done_from_true_to_false() -> None:
    """Toggle on done todo should mark it undone."""
    todo = Todo(id=1, text="test todo", done=True)
    assert todo.done is True

    result = todo.toggle()

    assert todo.done is False
    assert result is todo  # Returns self for chaining


def test_toggle_double_toggle_returns_to_original_state() -> None:
    """Toggle twice should return to original state."""
    todo = Todo(id=1, text="test todo")
    original_state = todo.done

    todo.toggle().toggle()

    assert todo.done == original_state


def test_toggle_updates_timestamp() -> None:
    """Toggle should update the updated_at timestamp."""
    todo = Todo(id=1, text="test todo")
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)
    todo.toggle()

    assert todo.updated_at > original_updated_at


def test_toggle_returns_todo_for_chaining() -> None:
    """Toggle should return the Todo instance for method chaining."""
    todo = Todo(id=1, text="test todo")

    # Should be able to chain multiple toggles
    result = todo.toggle().toggle().toggle()

    assert result is todo
    assert todo.done is True  # 3 toggles: False -> True -> False -> True
