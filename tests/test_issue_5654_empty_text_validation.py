"""Tests for empty/whitespace text validation in from_dict (Issue #5654).

These tests verify that Todo.from_dict rejects empty or whitespace-only text,
matching the behavior of Todo.rename() and TodoApp.add().
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_rejects_newline_only_text() -> None:
    """Todo.from_dict should reject newline-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\n\t"})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict should accept valid non-empty text."""
    todo = Todo.from_dict({"id": 1, "text": "valid task"})
    assert todo.text == "valid task"


def test_todo_from_dict_strips_whitespace_from_text() -> None:
    """Todo.from_dict should strip leading/trailing whitespace from text."""
    todo = Todo.from_dict({"id": 1, "text": "  valid task  "})
    assert todo.text == "valid task"
