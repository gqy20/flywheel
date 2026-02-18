"""Tests for issue #4243: Constructor text field validation.

Regression tests to ensure Todo constructor validates text field for empty strings,
consistent with the rename() method.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Todo constructor should raise ValueError for empty text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Todo constructor should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Todo constructor should succeed with valid text."""
    todo = Todo(id=1, text="valid")
    assert todo.text == "valid"
    assert todo.id == 1


def test_todo_constructor_strips_whitespace() -> None:
    """Todo constructor should strip leading/trailing whitespace from text."""
    todo = Todo(id=1, text="  valid text  ")
    assert todo.text == "valid text"
