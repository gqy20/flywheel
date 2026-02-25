"""Tests for empty/whitespace-only text validation (Issue #5817).

These tests verify that:
1. Todo construction with empty string raises ValueError in __post_init__
2. Todo.from_dict with empty text raises ValueError
3. Todo.from_dict with whitespace-only text raises ValueError
4. Valid text is still accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_construction_rejects_empty_string() -> None:
    """Todo construction with empty text should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_construction_rejects_whitespace_only() -> None:
    """Todo construction with whitespace-only text should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_from_dict_rejects_empty_string() -> None:
    """Todo.from_dict should reject empty text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only() -> None:
    """Todo.from_dict should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": " "})

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\t\n"})


def test_todo_construction_accepts_valid_text() -> None:
    """Todo construction with valid text should still work."""
    todo = Todo(id=1, text="valid todo")
    assert todo.text == "valid todo"


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict with valid text should still work."""
    todo = Todo.from_dict({"id": 1, "text": "valid todo"})
    assert todo.text == "valid todo"
