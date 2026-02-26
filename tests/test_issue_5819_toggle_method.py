"""Tests for toggle() method to flip done state (Issue #5819)."""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_flips_done_from_false_to_true() -> None:
    """toggle() should flip done from False to True."""
    todo = Todo(id=1, text="a", done=False)
    original_updated_at = todo.updated_at

    todo.toggle()

    assert todo.done is True
    assert todo.updated_at >= original_updated_at


def test_toggle_flips_done_from_true_to_false() -> None:
    """toggle() should flip done from True to False."""
    todo = Todo(id=1, text="a", done=True)
    original_updated_at = todo.updated_at

    todo.toggle()

    assert todo.done is False
    assert todo.updated_at >= original_updated_at


def test_toggle_can_flip_multiple_times() -> None:
    """toggle() should work correctly when called multiple times."""
    todo = Todo(id=1, text="a", done=False)

    todo.toggle()
    assert todo.done is True

    todo.toggle()
    assert todo.done is False

    todo.toggle()
    assert todo.done is True
