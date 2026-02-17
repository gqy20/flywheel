"""Tests for empty/whitespace text validation in from_dict (Issue #3965).

These tests verify that:
1. Todo.from_dict rejects empty string for 'text' field
2. Todo.from_dict rejects whitespace-only string for 'text' field
3. Todo.from_dict accepts valid non-empty text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|cannot be empty|blank"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|cannot be empty|blank"):
        Todo.from_dict({"id": 1, "text": " \t\n"})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict should accept valid non-empty text."""
    todo = Todo.from_dict({"id": 1, "text": "valid"})
    assert todo.text == "valid"
