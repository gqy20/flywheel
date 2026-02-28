"""Tests for Todo text field validation (Issue #6408).

These tests verify that:
1. Todo construction with empty string raises ValueError
2. Todo construction with whitespace-only string raises ValueError
3. Todo construction with valid text succeeds
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_empty_text_raises_value_error() -> None:
    """Todo construction with empty text should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_whitespace_only_text_raises_value_error() -> None:
    """Todo construction with whitespace-only text should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_whitespace_only_with_tabs_and_newlines_raises_value_error() -> None:
    """Todo construction with tabs and newlines only should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" \t\n ")


def test_todo_valid_text_succeeds() -> None:
    """Todo construction with valid text should succeed."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"


def test_todo_valid_text_with_leading_trailing_whitespace_succeeds() -> None:
    """Todo construction with text that has whitespace but actual content should succeed."""
    todo = Todo(id=1, text="  valid text  ")
    # Note: text should be preserved as-is (not stripped), validation only rejects empty/whitespace-only
    assert todo.text == "  valid text  "
