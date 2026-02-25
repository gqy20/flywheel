"""Tests for Todo text validation on construction (Issue #5801).

These tests verify that:
1. Todo construction rejects empty text
2. Todo construction rejects whitespace-only text
3. Todo construction strips leading/trailing whitespace from text
4. Todo.from_dict() also validates and strips text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_construction_rejects_empty_string() -> None:
    """Issue #5801: Todo construction should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_construction_rejects_whitespace_only() -> None:
    """Issue #5801: Todo construction should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_construction_strips_whitespace() -> None:
    """Issue #5801: Todo construction should strip leading/trailing whitespace."""
    todo = Todo(id=1, text=" valid ")
    assert todo.text == "valid"

    todo2 = Todo(id=2, text="\tspaced\t")
    assert todo2.text == "spaced"


def test_todo_from_dict_rejects_whitespace_only() -> None:
    """Issue #5801: Todo.from_dict() should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": " "})


def test_todo_from_dict_rejects_empty_string() -> None:
    """Issue #5801: Todo.from_dict() should reject empty text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_strips_whitespace() -> None:
    """Issue #5801: Todo.from_dict() should strip leading/trailing whitespace."""
    todo = Todo.from_dict({"id": 1, "text": " valid "})
    assert todo.text == "valid"
