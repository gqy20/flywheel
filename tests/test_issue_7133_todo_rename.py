"""Tests for Todo.rename method (Issue #7133).

These tests verify that:
1. Todo.rename successfully updates text for valid input
2. Empty string raises ValueError
3. Whitespace-only string raises ValueError
4. updated_at timestamp is updated after rename
"""

from __future__ import annotations

import time

import pytest

from flywheel.todo import Todo


def test_todo_rename_success() -> None:
    """rename('new text') should update self.text to 'new text'."""
    todo = Todo(id=1, text="original task")
    todo.rename("new task")

    assert todo.text == "new task"


def test_todo_rename_empty_string() -> None:
    """rename('') should raise ValueError."""
    todo = Todo(id=1, text="original task")

    with pytest.raises(ValueError, match="empty"):
        todo.rename("")


def test_todo_rename_whitespace_only() -> None:
    """rename('   ') should raise ValueError after stripping."""
    todo = Todo(id=1, text="original task")

    with pytest.raises(ValueError, match="empty"):
        todo.rename("   ")


def test_todo_rename_updates_timestamp() -> None:
    """rename should update updated_at timestamp."""
    todo = Todo(id=1, text="original task")
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    todo.rename("new task")

    # updated_at should have changed
    assert todo.updated_at != original_updated_at
