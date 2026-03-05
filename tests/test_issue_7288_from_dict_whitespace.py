"""Tests for from_dict whitespace handling (Issue #7288).

These tests verify that from_dict strips and validates text whitespace
to match rename() behavior and prevent empty strings after strip.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Bug #7288: Todo.from_dict should reject whitespace-only text strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "  "})


def test_todo_from_dict_rejects_various_whitespace_only_text() -> None:
    """Bug #7288: Todo.from_dict should reject various whitespace patterns."""
    # Single space
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": " "})

    # Tab and newline
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\t\n"})

    # Mixed whitespace
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": " \t \n "})


def test_todo_from_dict_strips_padded_text() -> None:
    """Bug #7288: Todo.from_dict should strip whitespace from padded text."""
    todo = Todo.from_dict({"id": 1, "text": "  task  "})
    assert todo.text == "task"


def test_todo_from_dict_strips_leading_whitespace() -> None:
    """Bug #7288: Todo.from_dict should strip leading whitespace."""
    todo = Todo.from_dict({"id": 1, "text": "   leading"})
    assert todo.text == "leading"


def test_todo_from_dict_strips_trailing_whitespace() -> None:
    """Bug #7288: Todo.from_dict should strip trailing whitespace."""
    todo = Todo.from_dict({"id": 1, "text": "trailing   "})
    assert todo.text == "trailing"


def test_todo_from_dict_preserves_internal_whitespace() -> None:
    """Bug #7288: Todo.from_dict should preserve internal whitespace after strip."""
    todo = Todo.from_dict({"id": 1, "text": "  hello world  "})
    assert todo.text == "hello world"


def test_todo_from_dict_accepts_valid_text() -> None:
    """Bug #7288: Todo.from_dict should still work with valid text."""
    todo = Todo.from_dict({"id": 1, "text": "valid task"})
    assert todo.text == "valid task"
