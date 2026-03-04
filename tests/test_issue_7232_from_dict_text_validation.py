"""Tests for from_dict text validation (Issue #7232).

These tests verify that:
1. Todo.from_dict rejects empty text strings
2. Todo.from_dict rejects whitespace-only text strings
3. Todo.from_dict accepts valid text strings

This ensures consistency with the rename() method which already validates
that text cannot be empty or whitespace-only.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|text"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|text"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_rejects_tab_only_text() -> None:
    """Todo.from_dict should reject tab-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|text"):
        Todo.from_dict({"id": 1, "text": "\t\t"})


def test_todo_from_dict_rejects_mixed_whitespace_text() -> None:
    """Todo.from_dict should reject mixed whitespace string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|text"):
        Todo.from_dict({"id": 1, "text": "  \t  \n  "})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict should accept valid non-empty text."""
    todo = Todo.from_dict({"id": 1, "text": "valid"})
    assert todo.text == "valid"


def test_todo_from_dict_accepts_text_with_leading_trailing_spaces() -> None:
    """Todo.from_dict should accept text with content, trimming whitespace like rename()."""
    todo = Todo.from_dict({"id": 1, "text": "  valid text  "})
    # Should be trimmed like rename() does
    assert todo.text == "valid text"
