"""Tests for empty/whitespace text validation in from_dict (Issue #5654).

These tests verify that Todo.from_dict rejects empty or whitespace-only text,
matching the behavior of Todo.rename() and TodoApp.add().
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty"):
        Todo.from_dict({"id": 1, "text": " \t\n"})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict should accept valid non-empty text."""
    todo = Todo.from_dict({"id": 1, "text": "valid"})
    assert todo.text == "valid"


def test_todo_from_dict_strips_and_preserves_text() -> None:
    """Todo.from_dict should preserve text with leading/trailing whitespace (not strip)."""
    # Unlike rename() which strips, from_dict should preserve the text as-is
    # after validating it's not empty after stripping
    todo = Todo.from_dict({"id": 1, "text": "  valid  "})
    assert todo.text == "  valid  "
