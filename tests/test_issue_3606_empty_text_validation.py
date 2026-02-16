"""Tests for Todo empty text validation (Issue #3606).

These tests verify that:
1. Todo(id=1, text='') raises ValueError
2. Todo(id=1, text=' ') raises ValueError
3. Todo(id=1, text='valid') succeeds
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_empty_text_raises_value_error() -> None:
    """Todo constructor should reject empty text string."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_whitespace_only_text_raises_value_error() -> None:
    """Todo constructor should reject whitespace-only text string."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_valid_text_succeeds() -> None:
    """Todo constructor should accept valid non-empty text."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"
    assert todo.id == 1


def test_todo_text_with_leading_trailing_whitespace_preserved() -> None:
    """Todo constructor should accept text with leading/trailing whitespace
    (it will be stripped during rename, but constructor accepts it)."""
    todo = Todo(id=1, text="  valid text with spaces  ")
    assert "valid text with spaces" in todo.text


def test_from_dict_empty_text_raises_value_error() -> None:
    """Todo.from_dict should reject empty text string."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_from_dict_whitespace_only_text_raises_value_error() -> None:
    """Todo.from_dict should reject whitespace-only text string."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})
