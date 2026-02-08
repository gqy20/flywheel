"""Tests for Todo text validation in __init__/__post_init__ (Issue #2264).

These tests verify that:
1. Todo.__init__/__post_init__ validates text is non-empty
2. Validation matches the behavior of rename() method
3. from_dict properly validates empty text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_empty_string() -> None:
    """Issue #2264: Todo() should reject empty string for text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_rejects_whitespace_only() -> None:
    """Issue #2264: Todo() should reject whitespace-only strings for text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   \t  \n  ")


def test_todo_init_accepts_valid_text() -> None:
    """Issue #2264: Todo() should still work with valid text."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"

    # Leading/trailing whitespace should be stripped
    todo2 = Todo(id=2, text="  padded  ")
    assert todo2.text == "padded"


def test_todo_from_dict_rejects_empty_text() -> None:
    """Issue #2264: Todo.from_dict() should reject empty text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Issue #2264: Todo.from_dict() should still work with valid text."""
    todo = Todo.from_dict({"id": 1, "text": "valid task"})
    assert todo.text == "valid task"

    # Whitespace should be stripped
    todo2 = Todo.from_dict({"id": 2, "text": "  padded  "})
    assert todo2.text == "padded"


def test_todo_init_with_timestamps_still_works() -> None:
    """Issue #2264: Existing timestamp initialization in __post_init__ should still work."""
    todo = Todo(id=1, text="task", created_at="2024-01-01T00:00:00+00:00")
    assert todo.created_at == "2024-01-01T00:00:00+00:00"
    assert todo.updated_at == "2024-01-01T00:00:00+00:00"

    # Default timestamps should be set if not provided
    todo2 = Todo(id=2, text="task2")
    assert todo2.created_at != ""
    assert todo2.updated_at != ""
