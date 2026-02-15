"""Tests for issue #3432: Todo constructor text validation.

Bug: Todo constructor does not validate that text parameter is non-empty.
The rename() method has this validation, but the constructor does not.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_text() -> None:
    """Bug #3432: Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only_text() -> None:
    """Bug #3432: Todo(id=1, text=' ') should raise ValueError after strip."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_from_dict_rejects_empty_text() -> None:
    """Bug #3432: Todo.from_dict with empty text should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Bug #3432: Todo.from_dict with whitespace-only text should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_constructor_accepts_valid_text() -> None:
    """Verify that valid text still works after the fix."""
    todo = Todo(id=1, text="valid todo")
    assert todo.text == "valid todo"


def test_todo_from_dict_accepts_valid_text() -> None:
    """Verify that Todo.from_dict with valid text still works after the fix."""
    todo = Todo.from_dict({"id": 1, "text": "valid todo"})
    assert todo.text == "valid todo"
