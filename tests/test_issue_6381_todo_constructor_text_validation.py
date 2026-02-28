"""Tests for Todo constructor text validation (Issue #6381).

These tests verify that:
1. Todo constructor rejects empty string for text
2. Todo constructor rejects whitespace-only string for text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Todo constructor should reject empty string for text field."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Todo constructor should reject whitespace-only string for text field."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_constructor_accepts_valid_text() -> None:
    """Todo constructor should accept valid non-empty text."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"


def test_todo_constructor_strips_whitespace() -> None:
    """Todo constructor should strip whitespace from text."""
    todo = Todo(id=1, text="  task with spaces  ")
    assert todo.text == "task with spaces"
