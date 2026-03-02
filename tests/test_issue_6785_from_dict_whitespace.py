"""Tests for Issue #6785 - Todo.from_dict should reject whitespace-only text.

These tests verify that:
1. from_dict rejects text that is only whitespace (spaces, tabs, newlines)
2. from_dict rejects empty string text
3. from_dict accepts valid text with leading/trailing spaces (stripped)
4. Roundtrip to_dict/from_dict preserves text content correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_whitespace_only_text_spaces() -> None:
    """from_dict should reject text that is only spaces."""
    with pytest.raises(ValueError, match=r"'text'.*empty|empty.*'text'"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_from_dict_rejects_whitespace_only_text_tabs_newlines() -> None:
    """from_dict should reject text that is only tabs and newlines."""
    with pytest.raises(ValueError, match=r"'text'.*empty|empty.*'text'"):
        Todo.from_dict({"id": 1, "text": "\t\n"})


def test_from_dict_rejects_empty_string_text() -> None:
    """from_dict should reject empty string text."""
    with pytest.raises(ValueError, match=r"'text'.*empty|empty.*'text'"):
        Todo.from_dict({"id": 1, "text": ""})


def test_from_dict_accepts_text_with_leading_trailing_spaces() -> None:
    """from_dict should accept valid text that has leading/trailing spaces (stripped)."""
    todo = Todo.from_dict({"id": 1, "text": "  valid  "})
    assert todo.text == "valid"


def test_from_dict_roundtrip_preserves_stripped_text() -> None:
    """Roundtrip to_dict/from_dict should work correctly."""
    original = Todo(id=1, text="my task")
    data = original.to_dict()
    restored = Todo.from_dict(data)
    assert restored.text == "my task"
