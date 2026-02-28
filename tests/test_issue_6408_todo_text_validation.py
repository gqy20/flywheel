"""Tests for issue #6408: Todo.__post_init__ text validation.

Bug: Todo.__post_init__ does not validate 'text' field, allowing empty
or whitespace-only text when constructing Todo directly.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_construction_rejects_empty_string() -> None:
    """Issue #6408: Todo() should reject empty text strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_construction_rejects_whitespace_only() -> None:
    """Issue #6408: Todo() should reject whitespace-only text strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_construction_accepts_valid_text() -> None:
    """Issue #6408: Todo() should still work with valid text."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"

    # Verify timestamps are set
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_todo_construction_strips_whitespace() -> None:
    """Issue #6408: Todo() should strip whitespace from text like rename() does."""
    todo = Todo(id=1, text="  padded text  ")
    assert todo.text == "padded text"
