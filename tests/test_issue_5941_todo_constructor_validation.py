"""Tests for Todo constructor text validation (Issue #5941).

These tests verify that:
1. Todo constructor rejects empty string text
2. Todo constructor rejects whitespace-only text
3. Todo constructor accepts valid text

This makes the constructor consistent with rename() validation.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Bug #5941: Todo constructor should reject empty string text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Bug #5941: Todo constructor should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Bug #5941: Todo constructor should accept valid text."""
    # Normal text should work
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"

    # Text with leading/trailing whitespace should be preserved at construction
    # (rename() strips it, but constructor may preserve - this is acceptable)
    todo2 = Todo(id=2, text="  padded  ")
    assert todo2.text == "  padded  "
