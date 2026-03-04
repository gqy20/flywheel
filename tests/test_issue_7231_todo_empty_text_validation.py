"""Tests for Todo empty text validation (Issue #7231).

These tests verify that Todo rejects empty or whitespace-only text
in __post_init__, matching the validation in rename() and TodoApp.add().
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_empty_text_raises_value_error() -> None:
    """Todo with empty text should raise ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="")


def test_todo_whitespace_only_text_raises_value_error() -> None:
    """Todo with whitespace-only text should raise ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_whitespace_only_text_with_tabs_raises_value_error() -> None:
    """Todo with tabs-only text should raise ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="\t\t")


def test_todo_whitespace_only_text_mixed_raises_value_error() -> None:
    """Todo with mixed whitespace text should raise ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="  \t  \n  ")


def test_todo_valid_text_succeeds() -> None:
    """Todo with valid text should be created normally."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"


def test_todo_text_with_leading_trailing_whitespace_succeeds() -> None:
    """Todo with text containing leading/trailing whitespace should be preserved."""
    # Unlike TodoApp.add() which strips text, direct Todo creation preserves text
    # But the text after stripping should still be non-empty
    todo = Todo(id=1, text="  valid text  ")
    assert todo.text == "  valid text  "


def test_todo_from_dict_empty_text_raises_value_error() -> None:
    """Todo.from_dict with empty text should raise ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_whitespace_text_raises_value_error() -> None:
    """Todo.from_dict with whitespace-only text should raise ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})
