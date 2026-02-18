"""Tests for Todo.from_dict() empty/whitespace text validation (Issue #4299).

These tests verify that from_dict() validates text is not empty or whitespace-only,
consistent with rename() and CLI add() methods.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_empty_text() -> None:
    """from_dict() should reject empty text strings."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_from_dict_rejects_whitespace_only_text() -> None:
    """from_dict() should reject whitespace-only text strings."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_from_dict_strips_and_stores_text() -> None:
    """from_dict() should strip whitespace and store cleaned text."""
    todo = Todo.from_dict({"id": 1, "text": "  valid task  "})
    assert todo.text == "valid task"


def test_from_dict_accepts_valid_text() -> None:
    """from_dict() should accept valid non-empty text."""
    todo = Todo.from_dict({"id": 1, "text": "buy milk"})
    assert todo.text == "buy milk"
