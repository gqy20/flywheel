"""Tests for issue #3184: Todo.__init__ text validation."""

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_empty_string() -> None:
    """Bug #3184: Todo.__init__ should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_rejects_whitespace_only() -> None:
    """Bug #3184: Todo.__init__ should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_init_accepts_valid_text() -> None:
    """Bug #3184: Todo.__init__ should still work with valid text."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"


def test_todo_init_strips_whitespace() -> None:
    """Bug #3184: Todo.__init__ should strip whitespace from text."""
    todo = Todo(id=1, text="  padded  ")
    assert todo.text == "padded"
