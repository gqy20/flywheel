"""Tests for issue #3705: Todo.__init__ should reject empty/whitespace-only text."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_empty_string() -> None:
    """Bug #3705: Todo.__init__ should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_rejects_whitespace_only() -> None:
    """Bug #3705: Todo.__init__ should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_init_accepts_valid_text() -> None:
    """Bug #3705: Todo.__init__ should still work with valid text."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"

    todo2 = Todo(id=2, text="  padded  ")
    assert todo2.text == "  padded  "
