"""Tests for toggle() method to simplify completion status switching.

Issue #3174: Add toggle() method to simplify done status switching.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_toggle_switches_false_to_true() -> None:
    """toggle() should switch done=False to done=True."""
    todo = Todo(id=1, text="test task", done=False)
    original_updated_at = todo.updated_at

    todo.toggle()

    assert todo.done is True
    assert todo.updated_at >= original_updated_at


def test_toggle_switches_true_to_false() -> None:
    """toggle() should switch done=True to done=False."""
    todo = Todo(id=1, text="test task", done=True)
    original_updated_at = todo.updated_at

    todo.toggle()

    assert todo.done is False
    assert todo.updated_at >= original_updated_at


def test_toggle_returns_none() -> None:
    """toggle() should return None for consistency with mark_done/undone."""
    todo = Todo(id=1, text="test task", done=False)

    result = todo.toggle()

    assert result is None
