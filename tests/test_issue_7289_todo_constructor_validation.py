"""Tests for Todo constructor text validation edge cases (Issue #7289).

These tests verify that the Todo constructor:
1. Rejects empty strings
2. Rejects whitespace-only strings
3. Strips whitespace from padded text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Todo constructor should reject empty string for text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Todo constructor should reject whitespace-only strings for text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_strips_whitespace() -> None:
    """Todo constructor should strip leading/trailing whitespace from text."""
    todo = Todo(id=1, text="  valid text  ")
    assert todo.text == "valid text"


def test_todo_constructor_accepts_valid_text() -> None:
    """Todo constructor should still work with valid text."""
    todo = Todo(id=1, text="hello world")
    assert todo.text == "hello world"
