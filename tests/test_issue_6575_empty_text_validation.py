"""Tests for consistent empty text validation (Issue #6575).

These tests verify that:
1. Todo constructor rejects empty/whitespace text (consistency with rename())
2. Todo.from_dict rejects empty/whitespace text (consistency with rename())
3. All entry points enforce the same text validation rules
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Issue #6575: Todo constructor should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Issue #6575: Todo constructor should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Issue #6575: Todo constructor should still work with valid text."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"


def test_todo_from_dict_rejects_empty_string() -> None:
    """Issue #6575: Todo.from_dict should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only() -> None:
    """Issue #6575: Todo.from_dict should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": " "})

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\t\n"})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Issue #6575: Todo.from_dict should still work with valid text."""
    todo = Todo.from_dict({"id": 1, "text": "valid text"})
    assert todo.text == "valid text"
