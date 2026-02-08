"""Tests for Issue #2304 - Todo.from_dict() text validation.

Bug: Todo.from_dict() does not validate that text field is non-empty after stripping,
unlike the rename() method which properly validates this.

Tests verify that from_dict() rejects empty/whitespace-only text and strips valid text.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_string() -> None:
    """Bug #2304: Todo.from_dict() should reject empty string text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only() -> None:
    """Bug #2304: Todo.from_dict() should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\t\n"})


def test_todo_from_dict_strips_valid_text() -> None:
    """Bug #2304: Todo.from_dict() should strip whitespace from valid text."""
    todo = Todo.from_dict({"id": 1, "text": "  valid  "})
    assert todo.text == "valid"
