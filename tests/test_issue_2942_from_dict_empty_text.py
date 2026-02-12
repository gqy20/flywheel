"""Tests for issue #2942: Todo.from_dict should reject empty/whitespace-only text."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_empty_string_text() -> None:
    """Bug #2942: Todo.from_dict() should reject empty strings for text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_from_dict_rejects_whitespace_only_text() -> None:
    """Bug #2942: Todo.from_dict() should reject whitespace-only strings for text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\t\n"})


def test_from_dict_accepts_valid_text() -> None:
    """Bug #2942: Todo.from_dict() should accept valid non-empty text."""
    todo = Todo.from_dict({"id": 1, "text": "valid"})
    assert todo.text == "valid"
    assert todo.id == 1


def test_from_dict_strips_whitespace_from_text() -> None:
    """Bug #2942: Todo.from_dict() should strip leading/trailing whitespace."""
    todo = Todo.from_dict({"id": 1, "text": "  valid  "})
    assert todo.text == "valid"
