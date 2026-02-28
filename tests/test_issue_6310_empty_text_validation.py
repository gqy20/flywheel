"""Tests for empty text validation in Todo construction (Issue #6310).

These tests verify that:
1. Todo(id=1, text="") raises ValueError with message 'Todo text cannot be empty'
2. Todo(id=1, text=" ") raises ValueError after whitespace strip
3. Todo(id=1, text="valid") continues to work
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_construction_rejects_empty_text() -> None:
    """Todo construction should reject empty text string."""
    with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_construction_rejects_whitespace_only_text() -> None:
    """Todo construction should reject whitespace-only text string."""
    with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_construction_accepts_valid_text() -> None:
    """Todo construction should accept valid non-empty text."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"


def test_todo_construction_strips_whitespace() -> None:
    """Todo construction should strip leading/trailing whitespace from text."""
    todo = Todo(id=1, text="  valid task  ")
    assert todo.text == "valid task"
