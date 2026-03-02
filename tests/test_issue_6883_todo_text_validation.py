"""Tests for issue #6883: Todo constructor should reject None and non-string text values."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_none_as_text() -> None:
    """Bug #6883: Todo(id=1, text=None) should raise ValueError."""
    with pytest.raises(ValueError, match="text must be a string"):
        Todo(id=1, text=None)  # type: ignore[arg-type]


def test_todo_constructor_rejects_integer_as_text() -> None:
    """Bug #6883: Todo(id=1, text=123) should raise ValueError."""
    with pytest.raises(ValueError, match="text must be a string"):
        Todo(id=1, text=123)  # type: ignore[arg-type]


def test_todo_constructor_accepts_valid_string() -> None:
    """Verify Todo(id=1, text='valid') works as before."""
    todo = Todo(id=1, text="valid")
    assert todo.text == "valid"
    assert todo.id == 1
    assert todo.done is False
