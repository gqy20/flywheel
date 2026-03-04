"""Tests for Todo empty text validation (Issue #7161).

These tests verify that:
1. Todo constructor rejects empty string for 'text' field
2. Todo constructor rejects whitespace-only string for 'text' field
3. Todo.from_dict() rejects empty text
4. Todo.from_dict() rejects whitespace-only text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Todo constructor should reject empty string for text field."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only_string() -> None:
    """Todo constructor should reject whitespace-only string for text field."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_constructor_accepts_valid_text() -> None:
    """Todo constructor should accept valid non-empty text."""
    todo = Todo(id=1, text="valid")
    assert todo.text == "valid"


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict() should reject empty string for text field."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict() should reject whitespace-only string for text field."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict() should accept valid non-empty text."""
    todo = Todo.from_dict({"id": 1, "text": "valid"})
    assert todo.text == "valid"
