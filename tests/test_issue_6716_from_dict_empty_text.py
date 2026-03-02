"""Tests for empty text validation in from_dict (Issue #6716).

These tests verify that Todo.from_dict rejects empty and whitespace-only text,
making it consistent with rename() and add() validation logic.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_string_text() -> None:
    """Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})
