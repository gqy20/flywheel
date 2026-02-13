"""Tests for issue #3110: Todo constructor should validate empty text.

Bug: Todo.rename() validates that text.strip() is not empty, but the Todo
constructor does not perform the same validation. This creates an inconsistency
where a Todo can be created with empty or whitespace-only text, but cannot be
renamed to the same value.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Bug #3110: Todo constructor should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Bug #3110: Todo constructor should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Bug #3110: Todo constructor should still work with valid text."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"


def test_todo_constructor_strips_whitespace() -> None:
    """Bug #3110: Todo constructor should strip whitespace like rename()."""
    todo = Todo(id=1, text="  padded  ")
    assert todo.text == "padded"
