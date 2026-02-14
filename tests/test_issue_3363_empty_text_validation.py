"""Tests for Issue #3363: Todo.__init__ empty text validation.

Bug: Todo.__init__ allows empty text string, but rename() rejects it - inconsistent validation.

These tests verify that:
1. Todo.__init__ rejects empty text strings
2. Todo.__init__ rejects whitespace-only text strings
3. Todo.from_dict rejects empty/whitespace-only text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_empty_string() -> None:
    """Todo.__init__ should reject empty strings for text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_rejects_whitespace_only() -> None:
    """Todo.__init__ should reject whitespace-only strings for text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_init_accepts_valid_text() -> None:
    """Todo.__init__ should accept valid non-empty text."""
    todo = Todo(id=1, text="valid todo")
    assert todo.text == "valid todo"

    # Single character should work
    todo2 = Todo(id=2, text="x")
    assert todo2.text == "x"


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should reject empty text strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only text strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\t\n"})
