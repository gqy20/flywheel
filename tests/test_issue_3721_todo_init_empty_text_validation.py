"""Regression tests for issue #3721: Todo.__init__ should validate empty text.

Bug: Todo.__init__ does NOT validate empty text, but add() and rename() do.
This allows creation of invalid Todo objects with empty or whitespace-only text.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_empty_string() -> None:
    """Bug #3721: Todo.__init__ should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_rejects_whitespace_only() -> None:
    """Bug #3721: Todo.__init__ should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="  \t  ")


def test_todo_from_dict_rejects_empty_text() -> None:
    """Bug #3721: Todo.from_dict should reject empty text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Bug #3721: Todo.from_dict should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_init_accepts_valid_text() -> None:
    """Bug #3721: Todo.__init__ should still work with valid text."""
    todo = Todo(id=1, text="valid todo")
    assert todo.text == "valid todo"


def test_todo_from_dict_accepts_valid_text() -> None:
    """Bug #3721: Todo.from_dict should still work with valid text."""
    todo = Todo.from_dict({"id": 1, "text": "valid todo"})
    assert todo.text == "valid todo"
