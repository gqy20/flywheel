"""Tests for Todo.rename method (Issue #7133).

These tests verify that:
1. rename method successfully updates text
2. rename method raises ValueError for empty strings
3. rename method raises ValueError for whitespace-only strings
4. rename method updates the updated_at timestamp
"""

from __future__ import annotations

import time

import pytest

from flywheel.todo import Todo


def test_todo_rename_success() -> None:
    """rename should successfully update todo text."""
    todo = Todo(id=1, text="original text", done=False)
    todo.rename("new text")

    assert todo.text == "new text"


def test_todo_rename_empty_string() -> None:
    """rename should raise ValueError for empty string."""
    todo = Todo(id=1, text="original text", done=False)

    with pytest.raises(ValueError, match=r"empty"):
        todo.rename("")


def test_todo_rename_whitespace_only() -> None:
    """rename should raise ValueError for whitespace-only string."""
    todo = Todo(id=1, text="original text", done=False)

    with pytest.raises(ValueError, match=r"empty"):
        todo.rename("   ")


def test_todo_rename_updates_timestamp() -> None:
    """rename should update the updated_at timestamp."""
    todo = Todo(id=1, text="original text", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.rename("new text")

    # updated_at should be different from original
    assert todo.updated_at != original_updated_at


def test_todo_rename_strips_whitespace() -> None:
    """rename should strip leading/trailing whitespace from text."""
    todo = Todo(id=1, text="original text", done=False)
    todo.rename("  text with spaces  ")

    assert todo.text == "text with spaces"
