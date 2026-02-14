"""Tests for Todo.__post_init__ text validation (Issue #3334).

These tests verify that:
1. Todo construction rejects empty strings for text field
2. Todo construction rejects whitespace-only strings for text field
3. Error message is consistent with rename() method
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_construction_rejects_empty_string() -> None:
    """Todo construction should reject empty string for text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_construction_rejects_whitespace_only_string() -> None:
    """Todo construction should reject whitespace-only strings for text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_construction_rejects_tabs_and_newlines() -> None:
    """Todo construction should reject strings with only tabs/newlines."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" \t\n ")


def test_todo_construction_accepts_valid_text() -> None:
    """Todo construction should accept valid text."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"


def test_todo_construction_strips_whitespace_from_valid_text() -> None:
    """Todo construction should strip leading/trailing whitespace from text."""
    todo = Todo(id=1, text="  valid text  ")
    assert todo.text == "valid text"
