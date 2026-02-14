"""Tests for whitespace-only text validation in Todo.from_dict (Issue #3241).

These tests verify that:
1. Todo.from_dict rejects whitespace-only text strings (consistency with rename())
2. Todo.from_dict still accepts valid text
3. Todo.from_dict strips whitespace from text (consistency with rename())
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_whitespace_only_spaces() -> None:
    """Todo.from_dict should reject whitespace-only text (only spaces)."""
    with pytest.raises(ValueError, match=r"empty|whitespace|text"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_rejects_whitespace_only_tabs_newlines() -> None:
    """Todo.from_dict should reject whitespace-only text (tabs and newlines)."""
    with pytest.raises(ValueError, match=r"empty|whitespace|text"):
        Todo.from_dict({"id": 1, "text": "\t\n"})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict should accept valid text as before."""
    todo = Todo.from_dict({"id": 1, "text": "valid text"})
    assert todo.text == "valid text"


def test_todo_from_dict_strips_whitespace_from_text() -> None:
    """Todo.from_dict should strip whitespace from text (consistency with rename())."""
    todo = Todo.from_dict({"id": 1, "text": "  valid text  "})
    assert todo.text == "valid text"
