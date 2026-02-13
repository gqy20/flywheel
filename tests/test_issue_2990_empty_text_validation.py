"""Tests for Todo text validation in __post_init__ (Issue #2990).

These tests verify that:
1. Todo construction rejects empty string for 'text' field
2. Todo construction rejects whitespace-only string for 'text' field
3. Todo.from_dict rejects empty/whitespace-only text
4. This is consistent with rename() and TodoApp.add() behavior
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_construction_rejects_empty_string() -> None:
    """Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_construction_rejects_whitespace_only_string() -> None:
    """Todo(id=1, text=' ') should raise ValueError (whitespace-only)."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_construction_accepts_valid_text() -> None:
    """Todo(id=1, text='valid') should work normally."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict({'id': 1, 'text': ' '}) should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict with valid text should work."""
    todo = Todo.from_dict({"id": 1, "text": "valid task"})
    assert todo.text == "valid task"


def test_todo_rename_still_rejects_empty_text() -> None:
    """Ensure rename() still rejects empty text (regression check)."""
    todo = Todo(id=1, text="original")
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        todo.rename("")
