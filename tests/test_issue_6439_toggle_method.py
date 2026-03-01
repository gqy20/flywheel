"""Tests for toggle() convenience method - Issue #6439."""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_from_undone_to_done() -> None:
    """Toggle on undone todo should set done=True and return True."""
    todo = Todo(id=1, text="test todo")
    assert todo.done is False

    result = todo.toggle()

    assert result is True
    assert todo.done is True


def test_toggle_from_done_to_undone() -> None:
    """Toggle on done todo should set done=False and return False."""
    todo = Todo(id=1, text="test todo", done=True)
    assert todo.done is True

    result = todo.toggle()

    assert result is False
    assert todo.done is False


def test_toggle_updates_timestamp() -> None:
    """Toggle should update the updated_at timestamp."""
    todo = Todo(id=1, text="test todo")
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    import time
    time.sleep(0.001)

    todo.toggle()

    assert todo.updated_at > original_updated_at
