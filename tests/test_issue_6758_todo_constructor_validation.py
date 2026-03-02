"""Tests for issue #6758: Todo constructor text validation.

Bug: Todo constructor accepts empty/whitespace-only text without validation,
while rename() validates it.

Fix: Add text validation in __post_init__ to match rename() behavior:
strip whitespace and raise ValueError if empty.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Bug #6758: Todo constructor should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Bug #6758: Todo constructor should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_strips_whitespace() -> None:
    """Bug #6758: Todo constructor should store stripped text."""
    todo = Todo(id=1, text="  valid  ")
    assert todo.text == "valid"


def test_todo_constructor_accepts_valid_text() -> None:
    """Bug #6758: Todo constructor should still work with valid text."""
    todo = Todo(id=1, text="normal todo")
    assert todo.text == "normal todo"
