"""Tests for issue #5369: toggle() method to flip done status."""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_on_undone_todo_sets_done_true() -> None:
    """toggle() on undone todo should set done=True."""
    todo = Todo(id=1, text="test todo", done=False)

    todo.toggle()

    assert todo.done is True


def test_toggle_on_done_todo_sets_done_false() -> None:
    """toggle() on done todo should set done=False."""
    todo = Todo(id=1, text="test todo", done=True)

    todo.toggle()

    assert todo.done is False


def test_toggle_updates_updated_at() -> None:
    """toggle() should update the updated_at timestamp."""
    todo = Todo(id=1, text="test todo", done=False)
    original_updated_at = todo.updated_at

    todo.toggle()

    assert todo.updated_at > original_updated_at


def test_toggle_is_testable_in_isolation() -> None:
    """Verify toggle() works without external dependencies."""
    todo = Todo(id=1, text="isolated test")

    # Toggle multiple times to verify state transitions
    todo.toggle()
    assert todo.done is True

    todo.toggle()
    assert todo.done is False

    todo.toggle()
    assert todo.done is True
