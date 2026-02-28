"""Tests for Todo empty text validation (Issue #6310).

These tests verify that:
1. Todo(id=1, text="") raises ValueError with message 'Todo text cannot be empty'
2. Todo(id=1, text=" ") raises ValueError after whitespace strip
3. Todo(id=1, text="valid") continues to work
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_empty_string_raises_value_error() -> None:
    """Todo construction with empty string text should raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="")
    assert "Todo text cannot be empty" in str(exc_info.value)


def test_todo_whitespace_only_raises_value_error() -> None:
    """Todo construction with whitespace-only text should raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="   ")
    assert "Todo text cannot be empty" in str(exc_info.value)


def test_todo_valid_text_succeeds() -> None:
    """Todo construction with valid text should succeed."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"


def test_todo_text_with_leading_trailing_whitespace_is_stripped() -> None:
    """Todo text with leading/trailing whitespace should be stripped."""
    todo = Todo(id=1, text="  valid task  ")
    assert todo.text == "valid task"
