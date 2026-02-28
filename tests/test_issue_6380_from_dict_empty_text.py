"""Tests for issue #6380: from_dict should reject empty text strings."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_empty_string() -> None:
    """Bug #6380: Todo.from_dict() should reject empty text strings."""
    with pytest.raises(ValueError, match=r"text.*empty|empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_from_dict_rejects_whitespace_only() -> None:
    """Bug #6380: Todo.from_dict() should reject whitespace-only text."""
    with pytest.raises(ValueError, match=r"text.*empty|empty"):
        Todo.from_dict({"id": 1, "text": "   "})

    with pytest.raises(ValueError, match=r"text.*empty|empty"):
        Todo.from_dict({"id": 1, "text": "\t\n"})


def test_from_dict_accepts_valid_text() -> None:
    """Bug #6380: Todo.from_dict() should accept valid text."""
    todo = Todo.from_dict({"id": 1, "text": "valid"})
    assert todo.text == "valid"


def test_from_dict_accepts_text_with_surrounding_whitespace() -> None:
    """Bug #6380: Todo.from_dict() should accept text with surrounding whitespace.

    Note: Unlike rename() which strips the text, from_dict preserves the original
    text to maintain backward compatibility with existing stored data.
    """
    todo = Todo.from_dict({"id": 1, "text": "  valid  "})
    # Text is preserved as-is (not stripped) for backward compatibility
    assert todo.text == "  valid  "
