"""Tests for Todo.from_dict text validation (Issue #7219).

These tests verify that Todo.from_dict rejects empty strings and whitespace-only
strings for the 'text' field, consistent with Todo.rename behavior.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_rejects_tab_whitespace_only_text() -> None:
    """Todo.from_dict should reject tab-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\t\t"})


def test_todo_from_dict_rejects_mixed_whitespace_only_text() -> None:
    """Todo.from_dict should reject mixed whitespace string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|cannot be empty"):
        Todo.from_dict({"id": 1, "text": "  \t  \n  "})


def test_todo_from_dict_preserves_valid_text_with_leading_trailing_spaces() -> None:
    """Todo.from_dict should preserve original whitespace in valid text (not strip)."""
    todo = Todo.from_dict({"id": 1, "text": " valid text "})
    assert todo.text == " valid text "


def test_todo_from_dict_accepts_normal_text() -> None:
    """Todo.from_dict should accept normal non-empty text."""
    todo = Todo.from_dict({"id": 1, "text": "Buy groceries"})
    assert todo.text == "Buy groceries"
