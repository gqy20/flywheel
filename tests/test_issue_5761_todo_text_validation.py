"""Tests for Todo constructor text validation (Issue #5761).

These tests verify that:
1. Todo constructor rejects empty text strings
2. Todo constructor rejects whitespace-only text strings
3. Todo constructor accepts valid non-empty text strings
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_text() -> None:
    """Todo constructor should raise ValueError for empty text."""
    with pytest.raises(ValueError, match="empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only_text() -> None:
    """Todo constructor should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError, match="empty"):
        Todo(id=1, text="   ")


def test_todo_constructor_rejects_tab_only_text() -> None:
    """Todo constructor should raise ValueError for tab-only text."""
    with pytest.raises(ValueError, match="empty"):
        Todo(id=1, text="\t\t")


def test_todo_constructor_rejects_mixed_whitespace_text() -> None:
    """Todo constructor should raise ValueError for mixed whitespace text."""
    with pytest.raises(ValueError, match="empty"):
        Todo(id=1, text="  \t  \n  ")


def test_todo_constructor_accepts_valid_text() -> None:
    """Todo constructor should accept valid non-empty text."""
    todo = Todo(id=1, text="buy milk")
    assert todo.text == "buy milk"


def test_todo_constructor_accepts_text_with_leading_trailing_spaces() -> None:
    """Todo constructor should accept text that becomes non-empty after strip."""
    # The fix should strip whitespace and accept text with actual content
    todo = Todo(id=1, text="  valid task  ")
    # Text should be stripped per rename() behavior
    assert todo.text.strip() == "valid task"


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should raise ValueError for empty text."""
    with pytest.raises(ValueError, match="empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError, match="empty"):
        Todo.from_dict({"id": 1, "text": "   "})
