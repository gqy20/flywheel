"""Tests for Todo constructor text validation (Issue #4006).

These tests verify that the Todo constructor validates text field for
empty/whitespace-only values, similar to how rename() does.

Regression test for: Todo constructor accepts empty/whitespace-only text
bypassing rename() validation.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Issue #4006: Todo constructor should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Issue #4006: Todo constructor should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Issue #4006: Todo constructor should still work with valid text."""
    todo = Todo(id=1, text="valid todo")
    assert todo.text == "valid todo"


def test_todo_from_dict_rejects_empty_string() -> None:
    """Issue #4006: Todo.from_dict should reject empty text strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only() -> None:
    """Issue #4006: Todo.from_dict should reject whitespace-only text strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": " "})

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\t\n"})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Issue #4006: Todo.from_dict should accept valid text."""
    todo = Todo.from_dict({"id": 1, "text": "valid todo"})
    assert todo.text == "valid todo"
