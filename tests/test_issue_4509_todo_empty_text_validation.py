"""Tests for issue #4509: Todo constructor should reject empty/whitespace-only text.

Bug: Todo constructor accepts empty/whitespace-only text without validation,
inconsistent with rename() and cli.add() which reject empty text.

Acceptance criteria:
- Todo(id=1, text="") raises ValueError with message containing 'empty'
- Todo(id=1, text="   ") raises ValueError with message containing 'empty'
- Todo(id=1, text="valid") still works correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Issue #4509: Todo() should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Issue #4509: Todo() should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Issue #4509: Todo() should still work with valid text."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"
    assert todo.id == 1
