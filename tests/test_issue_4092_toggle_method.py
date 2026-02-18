"""Tests for toggle method on Todo (Issue #4092)."""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_changes_done_from_false_to_true() -> None:
    """toggle() should change done=False to done=True."""
    todo = Todo(id=1, text="test", done=False)

    todo.toggle()

    assert todo.done is True


def test_toggle_changes_done_from_true_to_false() -> None:
    """toggle() should change done=True to done=False."""
    todo = Todo(id=1, text="test", done=True)

    todo.toggle()

    assert todo.done is False


def test_toggle_updates_updated_at_timestamp() -> None:
    """toggle() should update the updated_at timestamp."""
    todo = Todo(id=1, text="test", done=False)
    original_updated_at = todo.updated_at

    todo.toggle()

    assert todo.updated_at != original_updated_at
    assert todo.updated_at >= original_updated_at
