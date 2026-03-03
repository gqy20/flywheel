"""Tests for issue #7077: Todo constructor should strip text like rename()."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_strips_leading_trailing_whitespace() -> None:
    """Bug #7077: Todo constructor should strip whitespace from text."""
    # Constructor should strip whitespace like rename() does
    todo = Todo(id=1, text="  foo  ")
    assert todo.text == "foo", f"Expected 'foo', got {todo.text!r}"


def test_todo_constructor_strips_various_whitespace() -> None:
    """Bug #7077: Constructor should handle tabs and newlines."""
    todo = Todo(id=1, text="\t  hello world  \n")
    assert todo.text == "hello world"


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Bug #7077: Constructor should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_constructor_rejects_empty_after_strip() -> None:
    """Bug #7077: Constructor should reject text that becomes empty after strip."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_consistent_with_rename() -> None:
    """Bug #7077: Constructor and rename() should have identical whitespace behavior."""
    # Create todo with padded text
    todo = Todo(id=1, text="  initial  ")

    # Constructor should have stripped it
    assert todo.text == "initial"

    # Rename with padding should also strip
    todo.rename("  renamed  ")
    assert todo.text == "renamed"
