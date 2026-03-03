"""Tests for Todo.__init__ text validation (Issue #7050).

Bug: Todo.__init__ does not validate empty/whitespace-only text, but Todo.rename() does.
Fix: Add text validation in __post_init__ similar to rename() method.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_empty_string() -> None:
    """Bug #7050: Todo.__init__ should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_rejects_whitespace_only() -> None:
    """Bug #7050: Todo.__init__ should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_init_strips_whitespace_and_accepts_valid_text() -> None:
    """Bug #7050: Todo.__init__ should strip whitespace and accept valid text."""
    # Text with surrounding whitespace should be stripped
    todo = Todo(id=1, text="  valid text  ")
    assert todo.text == "valid text"


def test_todo_from_dict_rejects_empty_string() -> None:
    """Bug #7050: Todo.from_dict should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only() -> None:
    """Bug #7050: Todo.from_dict should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_strips_whitespace() -> None:
    """Bug #7050: Todo.from_dict should strip whitespace from text."""
    todo = Todo.from_dict({"id": 1, "text": "  valid text  "})
    assert todo.text == "valid text"


def test_todo_init_accepts_valid_text() -> None:
    """Bug #7050: Todo.__init__ should still work with valid text."""
    todo = Todo(id=1, text="valid todo text")
    assert todo.text == "valid todo text"
