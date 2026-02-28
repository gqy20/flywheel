"""Tests for Todo empty text validation (Issue #6310).

These tests verify that:
1. Todo construction with empty text raises ValueError
2. Todo construction with whitespace-only text raises ValueError
3. Todo construction with valid text succeeds
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_empty_text_raises_value_error() -> None:
    """Todo(id=1, text='') should raise ValueError with message 'Todo text cannot be empty'."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="")
    assert "Todo text cannot be empty" in str(exc_info.value)


def test_todo_whitespace_only_text_raises_value_error() -> None:
    """Todo(id=1, text=' ') should raise ValueError after whitespace strip."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="   ")
    assert "Todo text cannot be empty" in str(exc_info.value)


def test_todo_valid_text_succeeds() -> None:
    """Todo(id=1, text='valid') should work as expected."""
    todo = Todo(id=1, text="valid")
    assert todo.text == "valid"
    assert todo.id == 1


def test_todo_text_with_leading_trailing_whitespace_is_stripped() -> None:
    """Todo should strip whitespace from text during construction."""
    todo = Todo(id=1, text="  valid text  ")
    assert todo.text == "valid text"
