"""Tests for issue #5268: Todo dataclass should reject empty text strings.

Bug description:
    Todo dataclass allows empty text string, but Todo.rename() explicitly
    rejects it - inconsistent validation.

Fix:
    Add validation in Todo.__post_init__ to reject empty text, consistent
    with rename() behavior.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Issue #5268: Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Issue #5268: Todo should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Issue #5268: Todo construction with valid text should succeed."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"


def test_todo_constructor_strips_whitespace_from_text() -> None:
    """Issue #5268: Todo should strip whitespace from text, like rename() does."""
    todo = Todo(id=1, text="  padded text  ")
    assert todo.text == "padded text"
