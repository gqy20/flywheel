"""Tests for Todo empty text validation in __post_init__ (Issue #2990).

These tests verify that:
1. Todo construction rejects empty strings for 'text' field
2. Todo construction rejects whitespace-only strings for 'text' field
3. Todo.from_dict() also validates text is non-empty after strip
4. Valid text still works as expected
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_empty_string() -> None:
    """Bug #2990: Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_rejects_whitespace_only() -> None:
    """Bug #2990: Todo(id=1, text=' ') should raise ValueError."""
    # Single space
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    # Multiple whitespace characters
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_init_accepts_valid_text() -> None:
    """Bug #2990: Todo construction should still work with valid text."""
    todo = Todo(id=1, text="valid todo")
    assert todo.text == "valid todo"


def test_todo_init_strips_whitespace() -> None:
    """Bug #2990: Todo text should be stripped during construction."""
    todo = Todo(id=1, text="  padded text  ")
    assert todo.text == "padded text"


def test_todo_from_dict_rejects_empty_string() -> None:
    """Bug #2990: Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only() -> None:
    """Bug #2990: Todo.from_dict with whitespace-only text should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Bug #2990: Todo.from_dict with valid text should work."""
    todo = Todo.from_dict({"id": 1, "text": "valid todo"})
    assert todo.text == "valid todo"


def test_todo_from_dict_strips_whitespace() -> None:
    """Bug #2990: Todo.from_dict should strip text during construction."""
    todo = Todo.from_dict({"id": 1, "text": "  padded text  "})
    assert todo.text == "padded text"
