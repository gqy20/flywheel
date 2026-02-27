"""Tests for Todo empty text validation (Issue #6158).

These tests verify that:
1. Todo.__init__ rejects empty text with ValueError
2. Todo.__init__ rejects whitespace-only text with ValueError
3. Todo.from_dict rejects empty text with ValueError
4. Todo.from_dict rejects whitespace-only text with ValueError
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_empty_text() -> None:
    """Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_rejects_whitespace_only_text() -> None:
    """Todo(id=1, text='   ') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_init_rejects_tab_only_text() -> None:
    """Todo(id=1, text='\\t') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t")


def test_todo_init_rejects_newline_only_text() -> None:
    """Todo(id=1, text='\\n') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\n")


def test_todo_init_rejects_mixed_whitespace_only_text() -> None:
    """Todo(id=1, text='  \\t\\n  ') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="  \t\n  ")


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_init_accepts_valid_text() -> None:
    """Todo should accept valid non-empty text."""
    todo = Todo(id=1, text="buy milk")
    assert todo.text == "buy milk"


def test_todo_init_accepts_text_with_leading_trailing_whitespace() -> None:
    """Todo should accept text that has whitespace but also content."""
    todo = Todo(id=1, text="  buy milk  ")
    assert todo.text == "  buy milk  "
