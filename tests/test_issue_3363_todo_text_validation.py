"""Tests for Todo text validation (Issue #3363).

These tests verify that:
1. Todo.__init__ rejects empty text strings (matching rename() behavior)
2. Todo.__init__ rejects whitespace-only text strings
3. Todo.from_dict rejects empty/whitespace-only text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_empty_text() -> None:
    """Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_rejects_whitespace_only_text() -> None:
    """Todo(id=1, text='   ') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_init_rejects_tab_newline_whitespace() -> None:
    """Todo should reject text with only tabs and newlines."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n  ")


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict with empty text should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict with whitespace-only text should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_init_accepts_valid_text() -> None:
    """Todo should accept valid non-empty text."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"


def test_todo_init_strips_whitespace() -> None:
    """Todo should strip leading/trailing whitespace from text (like rename())."""
    todo = Todo(id=1, text="  valid task  ")
    assert todo.text == "valid task"
