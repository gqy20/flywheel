"""Tests for Todo constructor text validation (Issue #4819).

These tests verify that:
1. Todo constructor rejects empty text strings
2. Todo constructor rejects whitespace-only text strings
3. Todo constructor accepts valid text strings
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Todo constructor should raise ValueError for empty text."""
    with pytest.raises(ValueError, match="text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only_string() -> None:
    """Todo constructor should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError, match="text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_constructor_rejects_tabs_and_spaces() -> None:
    """Todo constructor should raise ValueError for tabs and spaces only."""
    with pytest.raises(ValueError, match="text cannot be empty"):
        Todo(id=1, text="\t  \n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Todo constructor should accept valid non-empty text."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"


def test_todo_constructor_strips_whitespace_from_valid_text() -> None:
    """Todo constructor should strip whitespace and store trimmed text."""
    todo = Todo(id=1, text="  valid task  ")
    assert todo.text == "valid task"


def test_todo_rename_still_validates() -> None:
    """Todo.rename() should continue to validate empty text."""
    todo = Todo(id=1, text="original")
    with pytest.raises(ValueError, match="text cannot be empty"):
        todo.rename("")
