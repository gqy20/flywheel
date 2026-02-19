"""Tests for Todo constructor text validation (Issue #4509).

These tests verify that:
1. Todo constructor rejects empty text
2. Todo constructor rejects whitespace-only text
3. Todo constructor accepts valid text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_text() -> None:
    """Todo constructor should reject empty text."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="")
    assert "empty" in str(exc_info.value).lower()


def test_todo_constructor_rejects_whitespace_only_text() -> None:
    """Todo constructor should reject whitespace-only text."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="   \t\n")
    assert "empty" in str(exc_info.value).lower()


def test_todo_constructor_accepts_valid_text() -> None:
    """Todo constructor should accept valid text."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"
    assert todo.id == 1
    assert todo.done is False


def test_todo_constructor_text_with_leading_trailing_spaces() -> None:
    """Todo constructor should accept text with surrounding spaces (they are preserved)."""
    todo = Todo(id=1, text="  valid text  ")
    # Text is stored as-is; rename() strips but constructor preserves
    assert todo.text == "  valid text  "
