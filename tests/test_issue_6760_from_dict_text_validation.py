"""Regression tests for Issue #6760: from_dict text field stripping and validation.

This test file ensures that:
1. Todo.from_dict strips whitespace from text field (matching rename() behavior)
2. Todo.from_dict rejects empty text after stripping
3. Todo.from_dict rejects whitespace-only text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should reject empty text string."""
    with pytest.raises(ValueError, match=r"empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only text."""
    with pytest.raises(ValueError, match=r"empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_strips_whitespace_from_text() -> None:
    """Todo.from_dict should strip leading/trailing whitespace from text."""
    todo = Todo.from_dict({"id": 1, "text": "  hello  "})
    assert todo.text == "hello"


def test_todo_from_dict_strips_tabs_and_newlines() -> None:
    """Todo.from_dict should strip tabs and newlines from text."""
    todo = Todo.from_dict({"id": 1, "text": "\t\n  task  \n\t"})
    assert todo.text == "task"


def test_todo_from_dict_preserves_internal_whitespace() -> None:
    """Todo.from_dict should preserve internal whitespace in text."""
    todo = Todo.from_dict({"id": 1, "text": "  buy groceries  "})
    assert todo.text == "buy groceries"
