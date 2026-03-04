"""Tests for Todo empty/whitespace text validation (Issue #7231).

These tests verify that:
1. Todo rejects empty text strings
2. Todo rejects whitespace-only text strings
3. Todo accepts valid text strings
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_rejects_empty_text() -> None:
    """Todo should raise ValueError for empty text."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="")


def test_todo_rejects_whitespace_only_text() -> None:
    """Todo should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_rejects_tab_only_text() -> None:
    """Todo should raise ValueError for tab-only text."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="\t")


def test_todo_rejects_newline_only_text() -> None:
    """Todo should raise ValueError for newline-only text."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="\n")


def test_todo_rejects_mixed_whitespace_text() -> None:
    """Todo should raise ValueError for mixed whitespace-only text."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="  \t\n  ")


def test_todo_accepts_valid_text() -> None:
    """Todo should accept valid text strings."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"


def test_todo_accepts_text_with_leading_trailing_spaces() -> None:
    """Todo should accept text that has content after stripping."""
    todo = Todo(id=1, text="  valid text  ")
    # Note: The fix should strip and store the stripped value
    assert todo.text.strip() == "valid text"


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should raise ValueError for empty text."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_text() -> None:
    """Todo.from_dict should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict should accept valid text."""
    todo = Todo.from_dict({"id": 1, "text": "valid text"})
    assert todo.text == "valid text"
