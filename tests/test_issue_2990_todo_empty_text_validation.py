"""Tests for Todo.__post_init__ empty text validation (Issue #2990).

These tests verify that:
1. Todo(id=1, text='') raises ValueError
2. Todo(id=1, text=' ') raises ValueError (whitespace-only)
3. Todo.from_dict({'id': 1, 'text': ''}) raises ValueError
4. Valid text still works normally
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_empty_string_raises_value_error() -> None:
    """Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_whitespace_only_raises_value_error() -> None:
    """Todo(id=1, text='   ') should raise ValueError (whitespace-only)."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_from_dict_empty_text_raises_value_error() -> None:
    """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_whitespace_only_text_raises_value_error() -> None:
    """Todo.from_dict with whitespace-only text should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_valid_text_still_works() -> None:
    """Todo with valid text should still work normally."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"
    assert todo.id == 1


def test_todo_text_is_stripped_on_construction() -> None:
    """Todo text should be stripped during construction (consistent with rename)."""
    todo = Todo(id=1, text="  padded text  ")
    assert todo.text == "padded text"


def test_todo_from_dict_with_valid_text_works() -> None:
    """Todo.from_dict with valid text should work normally."""
    todo = Todo.from_dict({"id": 1, "text": "valid"})
    assert todo.text == "valid"
    assert todo.id == 1
