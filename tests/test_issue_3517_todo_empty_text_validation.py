"""Tests for Todo constructor and from_dict text validation (Issue #3517).

These tests verify that:
1. Todo constructor rejects empty strings for text
2. Todo constructor rejects whitespace-only strings for text
3. Todo.from_dict rejects empty strings for text
4. Todo.from_dict rejects whitespace-only strings for text
5. Valid text still works correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Issue #3517: Todo constructor should reject empty strings for text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Issue #3517: Todo constructor should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="  \t\n")


def test_todo_from_dict_rejects_empty_string() -> None:
    """Issue #3517: Todo.from_dict should reject empty strings for text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only() -> None:
    """Issue #3517: Todo.from_dict should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "  "})

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "  \t\n"})


def test_todo_constructor_accepts_valid_text() -> None:
    """Issue #3517: Todo constructor should still work with valid text."""
    todo = Todo(id=1, text="valid")
    assert todo.text == "valid"


def test_todo_from_dict_accepts_valid_text() -> None:
    """Issue #3517: Todo.from_dict should still work with valid text."""
    todo = Todo.from_dict({"id": 1, "text": "valid"})
    assert todo.text == "valid"
