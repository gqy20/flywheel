"""Tests for issue #5229: Todo constructor should reject empty/whitespace-only text."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_whitespace_only_text() -> None:
    """Bug #5229: Todo constructor should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_constructor_rejects_newline_tab_whitespace() -> None:
    """Bug #5229: Todo constructor should reject text with only newline/tab."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\n\t")


def test_todo_constructor_accepts_valid_text() -> None:
    """Bug #5229: Todo constructor should accept valid text."""
    todo = Todo(id=1, text="valid")
    assert todo.text == "valid"


def test_todo_constructor_strips_whitespace_from_valid_text() -> None:
    """Bug #5229: Todo constructor should strip whitespace from valid text."""
    todo = Todo(id=1, text="  valid  ")
    assert todo.text == "valid"


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Bug #5229: Todo.from_dict() should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_rejects_tab_only_text() -> None:
    """Bug #5229: Todo.from_dict() should reject tab-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\t"})


def test_todo_from_dict_accepts_valid_text() -> None:
    """Bug #5229: Todo.from_dict() should accept valid text."""
    todo = Todo.from_dict({"id": 1, "text": "valid"})
    assert todo.text == "valid"


def test_todo_from_dict_strips_whitespace_from_valid_text() -> None:
    """Bug #5229: Todo.from_dict() should strip whitespace from valid text."""
    todo = Todo.from_dict({"id": 1, "text": "  valid  "})
    assert todo.text == "valid"
