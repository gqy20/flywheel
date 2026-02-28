"""Tests for Todo text field empty/whitespace validation (Issue #6281).

These tests verify that:
1. Todo.__init__ rejects empty text
2. Todo.__init__ rejects whitespace-only text
3. Todo.from_dict rejects empty text
4. Todo.from_dict rejects whitespace-only text
5. Valid text with leading/trailing whitespace is preserved (not auto-stripped)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_empty_text() -> None:
    """Todo.__init__ should raise ValueError for empty text."""
    with pytest.raises(ValueError, match=r"text.*empty|empty.*text"):
        Todo(id=1, text="")


def test_todo_init_rejects_whitespace_only_text() -> None:
    """Todo.__init__ should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError, match=r"text.*empty|empty.*text"):
        Todo(id=1, text="   ")


def test_todo_init_rejects_tab_only_text() -> None:
    """Todo.__init__ should raise ValueError for tab-only text."""
    with pytest.raises(ValueError, match=r"text.*empty|empty.*text"):
        Todo(id=1, text="\t\t")


def test_todo_init_rejects_mixed_whitespace_text() -> None:
    """Todo.__init__ should raise ValueError for mixed whitespace-only text."""
    with pytest.raises(ValueError, match=r"text.*empty|empty.*text"):
        Todo(id=1, text="  \t  \n  ")


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should raise ValueError for empty text."""
    with pytest.raises(ValueError, match=r"text.*empty|empty.*text"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError, match=r"text.*empty|empty.*text"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_init_accepts_valid_text() -> None:
    """Todo.__init__ should accept valid text."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"


def test_todo_init_preserves_text_whitespace() -> None:
    """Todo.__init__ should preserve leading/trailing whitespace in text.

    This is consistent with the rename() method which strips before validation
    but stores the stripped value. Here we just validate but don't strip.
    """
    todo = Todo(id=1, text=" valid text ")
    assert todo.text == " valid text "


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict should accept valid text."""
    todo = Todo.from_dict({"id": 1, "text": "valid task"})
    assert todo.text == "valid task"
