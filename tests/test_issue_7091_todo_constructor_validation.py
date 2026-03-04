"""Tests for Todo constructor validation (Issue #7091).

Bug: Todo constructor accepts empty and whitespace-only text, while rename() validates
against it - inconsistent validation allows creation of invalid todos via constructor
or from_dict.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Issue #7091: Todo constructor should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Issue #7091: Todo constructor should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_from_dict_rejects_empty_text() -> None:
    """Issue #7091: Todo.from_dict should reject empty text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Issue #7091: Todo.from_dict should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_constructor_accepts_valid_text() -> None:
    """Issue #7091: Todo constructor should still work with valid text."""
    todo = Todo(id=1, text="valid todo")
    assert todo.text == "valid todo"

    # Text with leading/trailing whitespace should be accepted (rename strips it)
    todo2 = Todo(id=2, text="  valid  ")
    assert todo2.text == "  valid  "
