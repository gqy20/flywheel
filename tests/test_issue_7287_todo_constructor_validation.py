"""Tests for Todo constructor text validation (Issue #7287).

These tests verify that:
1. Todo constructor strips whitespace from text like rename() does
2. Todo constructor rejects whitespace-only text like rename() does
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_strips_whitespace() -> None:
    """Todo constructor should strip leading/trailing whitespace from text."""
    todo = Todo(id=1, text="  task with padding  ")
    assert todo.text == "task with padding"


def test_todo_constructor_strips_leading_whitespace() -> None:
    """Todo constructor should strip leading whitespace."""
    todo = Todo(id=1, text="   task")
    assert todo.text == "task"


def test_todo_constructor_strips_trailing_whitespace() -> None:
    """Todo constructor should strip trailing whitespace."""
    todo = Todo(id=1, text="task   ")
    assert todo.text == "task"


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Todo constructor should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_constructor_rejects_empty_string() -> None:
    """Todo constructor should reject empty string text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_tabs_and_newlines_only() -> None:
    """Todo constructor should reject text with only tabs and newlines."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_preserves_internal_whitespace() -> None:
    """Todo constructor should preserve internal whitespace in valid text."""
    todo = Todo(id=1, text="  task with  multiple   spaces  ")
    assert todo.text == "task with  multiple   spaces"
