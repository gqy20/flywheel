"""Tests for from_dict text validation (Issue #5790).

These tests verify that:
1. Todo.from_dict rejects empty text strings
2. Todo.from_dict rejects whitespace-only text strings

This makes from_dict consistent with rename() and CLI add() validation.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|whitespace"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|whitespace"):
        Todo.from_dict({"id": 1, "text": "   "})
