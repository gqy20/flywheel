"""Tests for Todo.__post_init__ text validation (Issue #3334).

These tests verify that Todo construction validates the text field
to reject empty or whitespace-only strings, consistent with rename() behavior.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_construction_rejects_empty_string() -> None:
    """Bug #3334: Todo construction should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_construction_rejects_whitespace_only() -> None:
    """Bug #3334: Todo construction should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="  \t\n  ")


def test_todo_construction_accepts_valid_text() -> None:
    """Bug #3334: Todo construction should still work with valid text."""
    todo = Todo(id=1, text="valid todo")
    assert todo.text == "valid todo"


def test_todo_construction_strips_whitespace() -> None:
    """Bug #3334: Todo construction should strip whitespace from text."""
    todo = Todo(id=1, text="  padded  ")
    assert todo.text == "padded"
