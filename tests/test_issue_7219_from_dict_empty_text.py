"""Tests for Todo.from_dict text validation (Issue #7219).

These tests verify that Todo.from_dict rejects empty and whitespace-only
text values, consistent with Todo.rename behavior.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_string_text() -> None:
    """Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|text"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|text"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_preserves_whitespace_around_valid_text() -> None:
    """Todo.from_dict should preserve original whitespace around valid text.

    Unlike Todo.rename which strips whitespace, from_dict should preserve
    the original value when loading from storage.
    """
    todo = Todo.from_dict({"id": 1, "text": " valid "})
    assert todo.text == " valid "


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict should accept valid non-empty text."""
    todo = Todo.from_dict({"id": 1, "text": "buy groceries"})
    assert todo.text == "buy groceries"
