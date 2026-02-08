"""Tests for Todo text validation on initialization (Issue #2264).

These tests verify that:
1. Todo.__init__ validates that text is not empty or whitespace-only
2. Behavior is consistent with Todo.rename() method
3. from_dict also validates empty text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_empty_string() -> None:
    """Todo with empty string text should raise ValueError."""
    with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_rejects_whitespace_only() -> None:
    """Todo with whitespace-only text should raise ValueError."""
    with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_init_rejects_whitespace_with_tabs() -> None:
    """Todo with tabs and spaces should raise ValueError."""
    with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
        Todo(id=1, text="\t\n  ")


def test_todo_init_accepts_valid_text() -> None:
    """Todo with valid non-empty text should work."""
    todo = Todo(id=1, text="buy milk")
    assert todo.text == "buy milk"


def test_todo_init_trims_whitespace() -> None:
    """Todo should trim leading/trailing whitespace from text."""
    todo = Todo(id=1, text="  buy milk  ")
    assert todo.text == "buy milk"


def test_todo_rename_still_validates() -> None:
    """Todo.rename should still validate empty text after fix."""
    todo = Todo(id=1, text="original")
    with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
        todo.rename("")


def test_todo_from_dict_validates_empty_text() -> None:
    """Todo.from_dict should also validate empty text."""
    with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_validates_whitespace_text() -> None:
    """Todo.from_dict should validate whitespace-only text."""
    with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})
