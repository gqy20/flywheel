"""Tests for empty text validation in from_dict (Issue #6026).

These tests verify that Todo.from_dict rejects empty and whitespace-only
text strings, consistent with rename() and add() methods.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict should accept valid non-empty text."""
    todo = Todo.from_dict({"id": 1, "text": "valid text"})
    assert todo.text == "valid text"
    assert todo.id == 1


def test_todo_from_dict_accepts_text_with_leading_trailing_spaces() -> None:
    """Todo.from_dict should accept text that has non-empty content after strip."""
    todo = Todo.from_dict({"id": 1, "text": "  valid text  "})
    # Note: from_dict preserves the original text, unlike rename() which strips
    assert todo.text == "  valid text  "
