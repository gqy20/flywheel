"""Tests for text validation in from_dict (Issue #3433).

These tests verify that:
1. Empty text string is rejected with clear error message
2. Whitespace-only text is rejected with clear error message
3. Non-blank text still works normally
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should reject empty text string."""
    with pytest.raises(ValueError, match=r"text cannot be empty|empty.*text"):
        Todo.from_dict({"id": 1, "text": ""})


def test_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only text string."""
    with pytest.raises(ValueError, match=r"text cannot be empty|empty.*text"):
        Todo.from_dict({"id": 1, "text": " \t\n"})


def test_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict should accept non-blank text."""
    todo = Todo.from_dict({"id": 1, "text": "valid task"})
    assert todo.text == "valid task"


def test_from_dict_strips_whitespace_from_text() -> None:
    """Todo.from_dict should strip leading/trailing whitespace from text."""
    todo = Todo.from_dict({"id": 1, "text": "  valid task  "})
    assert todo.text == "valid task"
