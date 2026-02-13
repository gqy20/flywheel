"""Tests for text validation in from_dict (Issue #3002).

These tests verify that Todo.from_dict validates text is not empty/whitespace-only,
consistent with rename() and CLI add() behavior.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|blank"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|blank"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_accepts_valid_text_with_surrounding_whitespace() -> None:
    """Todo.from_dict should accept and strip whitespace from valid text."""
    todo = Todo.from_dict({"id": 1, "text": " valid text "})
    assert todo.text == "valid text"


def test_todo_from_dict_accepts_normal_text() -> None:
    """Todo.from_dict should accept normal text without issues."""
    todo = Todo.from_dict({"id": 1, "text": "Buy groceries"})
    assert todo.text == "Buy groceries"
