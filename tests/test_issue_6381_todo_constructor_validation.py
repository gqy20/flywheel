"""Tests for Todo constructor text validation (Issue #6381).

These tests verify that:
1. Todo constructor rejects empty string text
2. Todo constructor rejects whitespace-only text
3. The validation matches the rename() method behavior
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Todo(id, text='') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Todo(id, text='   ') should raise ValueError after strip."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Todo constructor should still work with valid text."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"


def test_todo_constructor_strips_whitespace() -> None:
    """Todo constructor should strip whitespace from text."""
    todo = Todo(id=1, text="  padded  ")
    assert todo.text == "padded"
