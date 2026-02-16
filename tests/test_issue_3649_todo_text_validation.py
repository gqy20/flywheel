"""Tests for issue #3649: Todo constructor and from_dict should validate empty text."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Issue #3649: Todo constructor should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Issue #3649: Todo constructor should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_strips_and_accepts_valid_text() -> None:
    """Issue #3649: Todo constructor should strip whitespace and accept valid text."""
    todo = Todo(id=1, text=" valid ")
    assert todo.text == "valid"


def test_todo_from_dict_rejects_empty_string() -> None:
    """Issue #3649: Todo.from_dict should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only() -> None:
    """Issue #3649: Todo.from_dict should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_strips_and_accepts_valid_text() -> None:
    """Issue #3649: Todo.from_dict should strip whitespace and accept valid text."""
    todo = Todo.from_dict({"id": 1, "text": " valid "})
    assert todo.text == "valid"
