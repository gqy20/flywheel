"""Tests for issue #7249: toggle() method to flip done status."""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_flips_false_to_true() -> None:
    """toggle() should flip done status from False to True."""
    todo = Todo(id=1, text="test todo", done=False)
    todo.toggle()
    assert todo.done is True


def test_toggle_flips_true_to_false() -> None:
    """toggle() should flip done status from True to False."""
    todo = Todo(id=1, text="test todo", done=True)
    todo.toggle()
    assert todo.done is False


def test_toggle_updates_updated_at() -> None:
    """toggle() should update updated_at timestamp."""
    todo = Todo(id=1, text="test todo", done=False)
    original_updated_at = todo.updated_at
    todo.toggle()
    assert todo.updated_at >= original_updated_at


def test_toggle_returns_self_for_chaining() -> None:
    """toggle() should return self for method chaining."""
    todo = Todo(id=1, text="test todo", done=False)
    result = todo.toggle()
    assert result is todo


def test_toggle_multiple_times_works() -> None:
    """toggle() should work correctly when called multiple times."""
    todo = Todo(id=1, text="test todo", done=False)

    todo.toggle()
    assert todo.done is True

    todo.toggle()
    assert todo.done is False

    todo.toggle()
    assert todo.done is True
