"""Tests for issue #3978: Todo constructor validation consistency.

Bug: Todo constructor accepts empty or whitespace-only text, but rename() rejects them.
Fix: Add validation in __post_init__ to ensure consistency with rename() and add().
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Issue #3978: Todo constructor should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Issue #3978: Todo constructor should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_from_dict_rejects_empty_string() -> None:
    """Issue #3978: Todo.from_dict should also reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only() -> None:
    """Issue #3978: Todo.from_dict should also reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_constructor_accepts_valid_text() -> None:
    """Verify Todo constructor still works with valid text."""
    todo = Todo(id=1, text="valid todo")
    assert todo.text == "valid todo"


def test_todo_from_dict_accepts_valid_text() -> None:
    """Verify Todo.from_dict still works with valid text."""
    todo = Todo.from_dict({"id": 1, "text": "valid todo"})
    assert todo.text == "valid todo"
