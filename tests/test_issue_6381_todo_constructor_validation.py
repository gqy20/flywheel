"""Tests for Todo constructor text validation (Issue #6381).

These tests verify that:
1. Todo constructor rejects empty text strings
2. Todo constructor rejects whitespace-only text strings
3. ValueError is raised with an appropriate message
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Todo constructor should reject empty text string."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="")
    assert "empty" in str(exc_info.value).lower()


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Todo constructor should reject whitespace-only text string."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="   ")
    assert "empty" in str(exc_info.value).lower()


def test_todo_constructor_accepts_valid_text() -> None:
    """Todo constructor should accept valid text."""
    todo = Todo(id=1, text="buy milk")
    assert todo.text == "buy milk"


def test_todo_constructor_accepts_text_with_leading_trailing_spaces() -> None:
    """Todo constructor should accept text with leading/trailing spaces (after stripping)."""
    todo = Todo(id=1, text="  buy milk  ")
    assert todo.text.strip() == "buy milk"
