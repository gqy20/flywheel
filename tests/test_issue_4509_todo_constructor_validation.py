"""Tests for Todo constructor validation - Issue #4509.

Bug: Todo constructor accepts empty/whitespace-only text without validation,
inconsistent with rename() and cli.add() which reject empty text.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Bug #4509: Todo constructor should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Bug #4509: Todo constructor should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="  \t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Bug #4509: Todo constructor should still work with valid text."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"
    assert todo.id == 1
    assert todo.done is False
