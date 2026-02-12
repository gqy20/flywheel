"""Tests for Todo.from_dict empty/whitespace text validation (Issue #2942).

These tests verify that Todo.from_dict rejects empty string and whitespace-only
text values, consistent with the rename() method's validation.

Acceptance criteria:
- Todo.from_dict({'id': 1, 'text': ''}) raises ValueError
- Todo.from_dict({'id': 1, 'text': '   '}) raises ValueError
- Todo.from_dict({'id': 1, 'text': 'valid'}) succeeds
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_string_text() -> None:
    """Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|whitespace"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|whitespace"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_rejects_tab_only_text() -> None:
    """Todo.from_dict should reject tab-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|whitespace"):
        Todo.from_dict({"id": 1, "text": "\t\t"})


def test_todo_from_dict_rejects_mixed_whitespace_text() -> None:
    """Todo.from_dict should reject mixed whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|whitespace"):
        Todo.from_dict({"id": 1, "text": "  \t  \n  "})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict should accept valid non-empty text."""
    todo = Todo.from_dict({"id": 1, "text": "valid"})
    assert todo.text == "valid"


def test_todo_from_dict_accepts_text_with_leading_trailing_spaces() -> None:
    """Todo.from_dict should accept text that has content after stripping spaces."""
    todo = Todo.from_dict({"id": 1, "text": "  valid  "})
    assert todo.text == "  valid  "  # Preserves original text with spaces
