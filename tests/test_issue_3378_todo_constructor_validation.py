"""Tests for issue #3378: Todo constructor text validation."""

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_none_text() -> None:
    """Bug #3378: Todo constructor should reject None for text field."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=None)  # type: ignore[arg-type]


def test_todo_constructor_rejects_empty_text() -> None:
    """Bug #3378: Todo constructor should reject empty strings for text field."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only_text() -> None:
    """Bug #3378: Todo constructor should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Bug #3378: Todo constructor should accept valid text."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"


def test_todo_constructor_strips_and_validates_text() -> None:
    """Bug #3378: Todo constructor should strip whitespace and validate."""
    # Text with leading/trailing whitespace should be accepted (stripped)
    todo = Todo(id=1, text="  valid task  ")
    assert todo.text == "valid task"
