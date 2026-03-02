"""Tests for Todo empty text validation (Issue #6813).

These tests verify that:
1. Todo constructor rejects empty text
2. Todo constructor rejects whitespace-only text
3. Todo.from_dict() rejects empty text
4. Todo constructor accepts valid non-empty text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_empty_text_raises_value_error() -> None:
    """Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_whitespace_only_text_raises_value_error() -> None:
    """Todo(id=1, text='   ') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_valid_text_succeeds() -> None:
    """Todo(id=1, text='valid') should succeed."""
    todo = Todo(id=1, text="valid")
    assert todo.text == "valid"


def test_todo_valid_text_with_leading_trailing_spaces_stripped() -> None:
    """Todo should strip leading/trailing whitespace from text."""
    todo = Todo(id=1, text="  valid text  ")
    assert todo.text == "valid text"


def test_todo_from_dict_empty_text_raises_value_error() -> None:
    """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_whitespace_text_raises_value_error() -> None:
    """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})
