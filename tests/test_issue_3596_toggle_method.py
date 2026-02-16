"""Tests for issue #3596: Add toggle() method to flip done status."""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_sets_done_to_true_when_undone() -> None:
    """Calling toggle() on undone todo sets done=True."""
    todo = Todo(id=1, text="test todo", done=False)
    original_updated_at = todo.updated_at

    todo.toggle()

    assert todo.done is True
    assert todo.updated_at != original_updated_at


def test_toggle_sets_done_to_false_when_done() -> None:
    """Calling toggle() on done todo sets done=False."""
    todo = Todo(id=1, text="test todo", done=True)
    original_updated_at = todo.updated_at

    todo.toggle()

    assert todo.done is False
    assert todo.updated_at != original_updated_at


def test_toggle_can_flip_multiple_times() -> None:
    """Toggle() can be called multiple times to flip status back and forth."""
    todo = Todo(id=1, text="test todo", done=False)

    todo.toggle()
    assert todo.done is True

    todo.toggle()
    assert todo.done is False

    todo.toggle()
    assert todo.done is True
