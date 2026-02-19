"""Tests for issue #4425: Todo text validation on construction."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_construction_rejects_whitespace_only_text() -> None:
    """Bug #4425: Todo() should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="  ")


def test_todo_construction_rejects_various_whitespace() -> None:
    """Bug #4425: Todo() should reject various whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   \t  \n  ")


def test_todo_construction_strips_padded_text() -> None:
    """Bug #4425: Todo() should strip whitespace from text."""
    todo = Todo(id=1, text="  padded  ")
    assert todo.text == "padded"


def test_todo_construction_accepts_valid_text() -> None:
    """Bug #4425: Todo() should still work with valid text."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Bug #4425: Todo.from_dict() should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "  "})


def test_todo_from_dict_strips_padded_text() -> None:
    """Bug #4425: Todo.from_dict() should strip whitespace from text."""
    todo = Todo.from_dict({"id": 1, "text": "  padded  "})
    assert todo.text == "padded"
