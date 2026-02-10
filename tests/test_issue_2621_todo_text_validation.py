"""Tests for Todo text validation in constructor (Issue #2621).

These tests verify that Todo constructor validates text content
to reject empty/whitespace-only strings at construction time,
matching the validation in Todo.rename() and TodoApp.add().
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Bug #2621: Todo constructor should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Bug #2621: Todo constructor should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="  ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\n")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\n\t")


def test_todo_constructor_accepts_valid_text() -> None:
    """Bug #2621: Todo constructor should accept valid text strings."""
    # Normal text
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"

    # Text with leading/trailing whitespace should be stripped
    todo2 = Todo(id=2, text="  padded task  ")
    assert todo2.text == "padded task"

    # Text with internal whitespace
    todo3 = Todo(id=3, text="task with spaces")
    assert todo3.text == "task with spaces"


def test_todo_from_dict_validates_text() -> None:
    """Bug #2621: from_dict should also validate text.

    Data from storage should be validated to catch manually
    edited or corrupted JSON files.
    """
    # from_dict should reject empty text (corrupted data)
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "", "done": False})

    # from_dict should reject whitespace-only text
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 2, "text": "   ", "done": False})

    # from_dict should strip whitespace from valid text
    todo = Todo.from_dict({"id": 3, "text": "  normal task  ", "done": True})
    assert todo.text == "normal task"
    assert todo.done is True
