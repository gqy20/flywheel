"""Tests for Todo.__init__ text type validation (Issue #7105).

These tests verify that:
1. Todo.__init__ validates 'text' is a string at construction time
2. Todo(id=1, text=123) raises ValueError
3. Todo(id=1, text=None) raises ValueError
4. Todo(id=1, text='valid') still works correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_integer_text() -> None:
    """Todo.__init__ should raise ValueError when text is an integer."""
    with pytest.raises(ValueError, match="'text' must be a string"):
        Todo(id=1, text=123)  # type: ignore[arg-type]


def test_todo_init_rejects_none_text() -> None:
    """Todo.__init__ should raise ValueError when text is None."""
    with pytest.raises(ValueError, match="'text' must be a string"):
        Todo(id=1, text=None)  # type: ignore[arg-type]


def test_todo_init_rejects_list_text() -> None:
    """Todo.__init__ should raise ValueError when text is a list."""
    with pytest.raises(ValueError, match="'text' must be a string"):
        Todo(id=1, text=["not", "a", "string"])  # type: ignore[arg-type]


def test_todo_init_rejects_dict_text() -> None:
    """Todo.__init__ should raise ValueError when text is a dict."""
    with pytest.raises(ValueError, match="'text' must be a string"):
        Todo(id=1, text={"key": "value"})  # type: ignore[arg-type]


def test_todo_init_accepts_valid_string() -> None:
    """Todo.__init__ should accept a valid string for text."""
    todo = Todo(id=1, text="valid string")
    assert todo.text == "valid string"
    assert todo.id == 1


def test_todo_init_accepts_empty_string() -> None:
    """Todo.__init__ should accept an empty string for text."""
    todo = Todo(id=1, text="")
    assert todo.text == ""
