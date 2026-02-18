"""Tests for Todo constructor text validation (Issue #4243).

These tests verify that:
1. Todo(id=1, text='') raises ValueError with message 'Todo text cannot be empty'
2. Todo(id=1, text='   ') raises ValueError (whitespace-only)
3. Todo(id=1, text='valid') succeeds
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_empty_string_raises_value_error() -> None:
    """Todo(id=1, text='') should raise ValueError with message 'Todo text cannot be empty'."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="")

    assert "Todo text cannot be empty" in str(exc_info.value)


def test_todo_whitespace_only_raises_value_error() -> None:
    """Todo(id=1, text='   ') should raise ValueError (whitespace-only)."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="   ")

    assert "Todo text cannot be empty" in str(exc_info.value)


def test_todo_valid_text_succeeds() -> None:
    """Todo(id=1, text='valid') should succeed."""
    todo = Todo(id=1, text="valid")

    assert todo.id == 1
    assert todo.text == "valid"
    assert todo.done is False


def test_todo_text_stripped_on_creation() -> None:
    """Todo should strip whitespace from text on creation (consistency with rename())."""
    todo = Todo(id=1, text="  valid with spaces  ")

    assert todo.text == "valid with spaces"


def test_todo_tab_whitespace_raises_value_error() -> None:
    """Todo(id=1, text='\\t\\t') should raise ValueError (whitespace-only)."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="\t\t")

    assert "Todo text cannot be empty" in str(exc_info.value)


def test_todo_mixed_whitespace_raises_value_error() -> None:
    """Todo(id=1, text=' \\t \\n ') should raise ValueError (whitespace-only)."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text=" \t \n ")

    assert "Todo text cannot be empty" in str(exc_info.value)
