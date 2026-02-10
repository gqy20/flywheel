"""Tests for Todo constructor validation (Issue #2621).

These tests verify that:
1. Todo constructor validates empty text when instantiated directly
2. Todo.from_dict validates empty text
3. Whitespace-only text is rejected
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Todo() should raise ValueError for empty text string."""
    with pytest.raises(ValueError, match="text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Todo() should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError, match="text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_constructor_accepts_valid_text() -> None:
    """Todo() should accept valid non-empty text."""
    todo = Todo(id=1, text="buy milk")
    assert todo.text == "buy milk"


def test_todo_constructor_accepts_text_with_internal_spaces() -> None:
    """Todo() should accept text with internal spaces."""
    todo = Todo(id=1, text="  buy milk  ")
    assert todo.text == "  buy milk  "


def test_todo_from_dict_rejects_empty_string() -> None:
    """Todo.from_dict() should raise ValueError for empty text."""
    with pytest.raises(ValueError, match="text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only() -> None:
    """Todo.from_dict() should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError, match="text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict() should accept valid non-empty text."""
    todo = Todo.from_dict({"id": 1, "text": "buy milk"})
    assert todo.text == "buy milk"
