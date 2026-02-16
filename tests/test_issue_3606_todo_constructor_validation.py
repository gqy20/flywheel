"""Regression tests for issue #3606.

Bug: Todo constructor allows empty or whitespace-only text, but rename() rejects them.

The Todo class should validate text in the constructor consistently with rename(),
raising ValueError for empty or whitespace-only strings.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Bug #3606: Todo constructor should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Bug #3606: Todo constructor should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Bug #3606: Todo constructor should accept valid text."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"


def test_todo_constructor_preserves_existing_behavior_for_rename() -> None:
    """Verify that rename() still validates after constructor fix."""
    todo = Todo(id=1, text="original")

    # rename() should still reject empty strings
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        todo.rename("")

    # rename() should still reject whitespace-only
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        todo.rename("   ")
