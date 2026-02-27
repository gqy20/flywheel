"""Tests for issue #6146: toggle() method to flip done status."""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_flips_false_to_true() -> None:
    """Issue #6146: toggle() should flip done from False to True."""
    todo = Todo(id=1, text="test task")
    assert todo.done is False

    result = todo.toggle()

    assert todo.done is True
    assert result is todo  # Returns self for chaining


def test_toggle_flips_true_to_false() -> None:
    """Issue #6146: toggle() should flip done from True to False."""
    todo = Todo(id=1, text="test task", done=True)
    assert todo.done is True

    result = todo.toggle()

    assert todo.done is False
    assert result is todo  # Returns self for chaining


def test_toggle_updates_timestamp() -> None:
    """Issue #6146: toggle() should update updated_at timestamp."""
    todo = Todo(id=1, text="test task")
    original_updated_at = todo.updated_at

    todo.toggle()

    assert todo.updated_at >= original_updated_at


def test_toggle_supports_method_chaining() -> None:
    """Issue #6146: toggle() returns self for method chaining."""
    todo = Todo(id=1, text="test task")

    # Should be able to chain multiple calls
    todo.toggle().toggle()

    assert todo.done is False  # Two toggles should return to original state
