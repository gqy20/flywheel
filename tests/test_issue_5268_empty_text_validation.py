"""Tests for issue #5268: Todo dataclass empty text validation.

Bug: Todo dataclass allows empty text string, but Todo.rename() explicitly rejects it.

This test ensures that Todo construction validates empty text consistently with rename().
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_construction_rejects_empty_string() -> None:
    """Bug #5268: Todo construction should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_construction_rejects_whitespace_only() -> None:
    """Bug #5268: Todo construction should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_construction_accepts_valid_text() -> None:
    """Bug #5268: Todo construction should still work with valid text."""
    todo = Todo(id=1, text="valid todo")
    assert todo.text == "valid todo"


def test_todo_construction_strips_whitespace_from_text() -> None:
    """Bug #5268: Todo construction should strip whitespace like rename()."""
    todo = Todo(id=1, text="  padded  ")
    assert todo.text == "padded"


def test_todo_from_dict_rejects_empty_string() -> None:
    """Bug #5268: Todo.from_dict should also reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only() -> None:
    """Bug #5268: Todo.from_dict should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})
