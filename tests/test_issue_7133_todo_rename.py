"""Tests for Todo.rename method (Issue #7133).

These tests verify that:
1. Todo.rename updates text to a new value
2. Todo.rename raises ValueError for empty strings
3. Todo.rename raises ValueError for whitespace-only strings
4. Todo.rename updates the updated_at timestamp
"""

from __future__ import annotations

import time

import pytest

from flywheel.todo import Todo


def test_todo_rename_success() -> None:
    """rename('new text') should update self.text to 'new text'."""
    todo = Todo(id=1, text="original text", done=False)
    todo.rename("new text")

    assert todo.text == "new text"


def test_todo_rename_empty_string() -> None:
    """rename('') should raise ValueError."""
    todo = Todo(id=1, text="original text", done=False)

    with pytest.raises(ValueError, match="empty"):
        todo.rename("")


def test_todo_rename_whitespace_only() -> None:
    """rename('   ') should raise ValueError."""
    todo = Todo(id=1, text="original text", done=False)

    with pytest.raises(ValueError, match="empty"):
        todo.rename("   ")


def test_todo_rename_updates_timestamp() -> None:
    """rename should update updated_at timestamp."""
    todo = Todo(id=1, text="original text", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.rename("new text")

    # updated_at should have changed
    assert todo.updated_at != original_updated_at


def test_todo_rename_strips_whitespace() -> None:
    """rename should strip leading/trailing whitespace from text."""
    todo = Todo(id=1, text="original text", done=False)
    todo.rename("  padded text  ")

    assert todo.text == "padded text"
