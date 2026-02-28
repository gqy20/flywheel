"""Tests for Todo text validation in __post_init__ (Issue #6408).

These tests verify that:
1. Todo construction rejects empty strings
2. Todo construction rejects whitespace-only strings
3. Todo construction accepts valid text
4. Text is stripped of leading/trailing whitespace
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_construction_rejects_empty_string() -> None:
    """Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_construction_rejects_whitespace_only() -> None:
    """Todo(id=1, text=' ') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_construction_accepts_valid_text() -> None:
    """Todo(id=1, text='valid') should work normally."""
    todo = Todo(id=1, text="valid")
    assert todo.text == "valid"


def test_todo_construction_strips_whitespace() -> None:
    """Todo should strip whitespace from text (consistent with rename())."""
    todo = Todo(id=1, text="  valid  ")
    assert todo.text == "valid"
