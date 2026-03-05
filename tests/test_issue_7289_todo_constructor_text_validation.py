"""Tests for Todo constructor text validation edge cases (Issue #7289).

These tests verify that the Todo constructor properly validates text:
1. Rejects empty string
2. Rejects whitespace-only strings
3. Strips surrounding whitespace
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Todo constructor should reject empty string for text field."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Todo constructor should reject whitespace-only strings for text field."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_strips_whitespace() -> None:
    """Todo constructor should strip leading/trailing whitespace from text."""
    todo = Todo(id=1, text="  valid  ")
    assert todo.text == "valid"

    todo2 = Todo(id=1, text="\t  padded text  \n")
    assert todo2.text == "padded text"
