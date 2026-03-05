"""Tests for issue #7288: from_dict should strip/validate text whitespace like rename() does."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_whitespace_only_text() -> None:
    """Bug #7288: Todo.from_dict() should reject whitespace-only text."""
    # Whitespace-only strings should raise ValueError
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "  "})

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\t\n"})


def test_from_dict_strips_whitespace_from_text() -> None:
    """Bug #7288: Todo.from_dict() should strip leading/trailing whitespace from text."""
    todo = Todo.from_dict({"id": 1, "text": "  task  "})
    assert todo.text == "task"


def test_from_dict_accepts_valid_text() -> None:
    """Bug #7288: Todo.from_dict() should still work with valid text."""
    todo = Todo.from_dict({"id": 1, "text": "valid task"})
    assert todo.text == "valid task"
