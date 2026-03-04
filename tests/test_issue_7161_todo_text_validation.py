"""Tests for Todo constructor text validation (Issue #7161).

These tests verify that:
1. Todo constructor rejects empty string for 'text' field
2. Todo constructor rejects whitespace-only string for 'text' field
3. Todo.from_dict rejects empty/whitespace-only text
4. Valid text still works as expected
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Bug #7161: Todo constructor should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Bug #7161: Todo constructor should reject whitespace-only strings for 'text' field."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Bug #7161: Todo constructor should still work with valid text."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"


def test_todo_from_dict_rejects_empty_text() -> None:
    """Bug #7161: Todo.from_dict should reject empty text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Bug #7161: Todo.from_dict should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})
