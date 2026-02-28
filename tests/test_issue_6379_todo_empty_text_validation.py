"""Tests for Todo empty text validation in __post_init__ (Issue #6379).

These tests verify that:
1. Todo(id=1, text='') raises ValueError
2. Todo(id=1, text='   ') raises ValueError
3. Todo(id=1, text='valid text') succeeds
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_empty_string_raises_value_error() -> None:
    """Todo with empty string text should raise ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="")


def test_todo_whitespace_only_raises_value_error() -> None:
    """Todo with whitespace-only text should raise ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_valid_text_succeeds() -> None:
    """Todo with valid text should be created successfully."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"


def test_todo_text_with_leading_trailing_whitespace_is_preserved() -> None:
    """Todo with text that has whitespace around meaningful content should succeed."""
    todo = Todo(id=1, text="  valid text  ")
    # Note: We preserve the text as-is during construction
    # The rename() method strips whitespace
    assert todo.text == "  valid text  "
