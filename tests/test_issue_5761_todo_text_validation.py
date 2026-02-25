"""Tests for Todo constructor text validation (Issue #5761).

These tests verify that:
1. Todo constructor validates text is a non-empty string after strip
2. Empty text raises ValueError
3. Whitespace-only text raises ValueError
4. Valid text succeeds
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_empty_text_raises_value_error() -> None:
    """Todo constructor should raise ValueError for empty text."""
    with pytest.raises(ValueError, match="text cannot be empty"):
        Todo(id=1, text="")


def test_todo_whitespace_only_text_raises_value_error() -> None:
    """Todo constructor should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError, match="text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_whitespace_text_with_tabs_and_newlines_raises_value_error() -> None:
    """Todo constructor should raise ValueError for text with only tabs/newlines."""
    with pytest.raises(ValueError, match="text cannot be empty"):
        Todo(id=1, text="\t\n  ")


def test_todo_valid_text_succeeds() -> None:
    """Todo constructor should succeed with valid text."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"


def test_todo_text_with_leading_trailing_whitespace_succeeds() -> None:
    """Todo constructor should succeed if text is non-empty after strip."""
    # Note: The constructor validates but does not strip - stripping is done by rename()
    todo = Todo(id=1, text="  valid task  ")
    # Text is validated (non-empty after strip) but not modified
    assert todo.text == "  valid task  "
