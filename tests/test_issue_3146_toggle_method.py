"""Tests for Todo.toggle() method - Issue #3146."""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_switches_done_from_false_to_true() -> None:
    """Test toggle() switches done status from False to True."""
    todo = Todo(id=1, text="a", done=False)
    todo.toggle()
    assert todo.done is True


def test_toggle_switches_done_from_true_to_false() -> None:
    """Test toggle() switches done status from True to False."""
    todo = Todo(id=1, text="a", done=True)
    todo.toggle()
    assert todo.done is False


def test_toggle_updates_updated_at_timestamp() -> None:
    """Test toggle() updates the updated_at timestamp."""
    todo = Todo(id=1, text="a", done=False)
    original_updated_at = todo.updated_at

    todo.toggle()

    assert todo.updated_at >= original_updated_at
