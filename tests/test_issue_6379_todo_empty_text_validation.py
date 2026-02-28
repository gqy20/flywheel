"""Tests for Todo empty text validation in __post_init__ (Issue #6379).

These tests verify that:
1. Todo construction with empty string text raises ValueError
2. Todo construction with whitespace-only text raises ValueError
3. Todo construction with valid text succeeds
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_empty_text_raises_value_error() -> None:
    """Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError, match="text cannot be empty"):
        Todo(id=1, text="")


def test_todo_whitespace_only_text_raises_value_error() -> None:
    """Todo(id=1, text='   ') should raise ValueError."""
    with pytest.raises(ValueError, match="text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_valid_text_succeeds() -> None:
    """Todo(id=1, text='valid text') should succeed."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"


def test_todo_text_with_leading_trailing_whitespace_succeeds() -> None:
    """Todo with text that has whitespace but also content should succeed."""
    todo = Todo(id=1, text="  valid text  ")
    assert todo.text == "  valid text  "
