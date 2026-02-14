"""Tests for Todo text field validation in constructor (Issue #3378).

These tests verify that:
1. Todo constructor rejects None for text field
2. Todo constructor rejects empty strings for text field
3. Todo constructor rejects whitespace-only strings for text field
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_none_text() -> None:
    """Todo constructor should reject None for text field."""
    with pytest.raises(ValueError, match=r"text cannot be empty|empty"):
        Todo(id=1, text=None)  # type: ignore[arg-type]


def test_todo_constructor_rejects_empty_text() -> None:
    """Todo constructor should reject empty string for text field."""
    with pytest.raises(ValueError, match=r"text cannot be empty|empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only_text() -> None:
    """Todo constructor should reject whitespace-only string for text field."""
    with pytest.raises(ValueError, match=r"text cannot be empty|empty"):
        Todo(id=1, text="   ")


def test_todo_constructor_accepts_valid_text() -> None:
    """Todo constructor should accept valid non-empty text."""
    todo = Todo(id=1, text="Buy groceries")
    assert todo.text == "Buy groceries"


def test_todo_constructor_strips_whitespace() -> None:
    """Todo constructor should strip whitespace from text."""
    todo = Todo(id=1, text="  Buy groceries  ")
    assert todo.text == "Buy groceries"
