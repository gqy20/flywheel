"""Tests for issue #3110: Todo constructor should validate empty text.

Bug: Todo.rename() and Todo constructor have inconsistent empty text validation.
The rename() method validates that stripped text is not empty, but the constructor
accepts empty strings and whitespace-only text without validation.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Issue #3110: Todo constructor should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Issue #3110: Todo constructor should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Issue #3110: Todo constructor should still work with valid text."""
    todo = Todo(id=1, text="valid todo")
    assert todo.text == "valid todo"


def test_todo_constructor_strips_whitespace() -> None:
    """Issue #3110: Todo constructor should strip whitespace like rename()."""
    todo = Todo(id=1, text="  padded  ")
    assert todo.text == "padded"
