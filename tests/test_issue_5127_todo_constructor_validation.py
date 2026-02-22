"""Tests for Todo constructor validation (Issue #5127).

These tests verify that the Todo constructor validates text consistently
with the rename() method - rejecting empty and whitespace-only text.

Before the fix, Todo constructor accepted empty text, but rename() did not,
which was inconsistent behavior.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_text() -> None:
    """Todo(id=1, text='') should raise ValueError for empty text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only_text() -> None:
    """Todo(id=1, text='   ') should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_constructor_rejects_tabs_and_newlines_only() -> None:
    """Todo should raise ValueError for text with only tabs/newlines."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n  ")


def test_todo_constructor_accepts_valid_text() -> None:
    """Todo(id=1, text='valid') should work as before."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_todo_constructor_strips_text_and_rejects_if_empty() -> None:
    """Todo should strip text and reject if result is empty."""
    # Text with leading/trailing whitespace should be stripped and still be valid
    todo = Todo(id=1, text="  valid task  ")
    assert todo.text == "  valid task  "  # Constructor doesn't strip, just validates

    # But whitespace-only should fail
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="  \t  ")


def test_todo_constructor_validation_matches_rename_validation() -> None:
    """Todo constructor validation should match rename() validation behavior."""
    # Both should raise same error for empty text
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")

    # rename() also rejects empty
    todo = Todo(id=1, text="valid")
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        todo.rename("")
