"""Tests for issue #4819: Todo constructor should validate text is not empty."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Bug #4819: Todo() should reject empty strings for text field."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Bug #4819: Todo() should reject whitespace-only strings for text field."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Bug #4819: Todo() should accept valid non-empty text."""
    todo = Todo(id=1, text="valid todo")
    assert todo.text == "valid todo"


def test_todo_constructor_strips_whitespace_from_valid_text() -> None:
    """Bug #4819: Todo() should strip whitespace from text (consistent with rename)."""
    todo = Todo(id=1, text="  padded  ")
    assert todo.text == "padded"
