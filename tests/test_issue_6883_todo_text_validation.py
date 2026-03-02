"""Tests for Todo text type validation (Issue #6883).

These tests verify that:
1. Todo constructor rejects None as text value
2. Todo constructor rejects non-string types as text value
3. Todo constructor accepts valid string text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_none_as_text() -> None:
    """Todo(id=1, text=None) should raise ValueError."""
    with pytest.raises(ValueError, match="'text' must be a string"):
        Todo(id=1, text=None)  # type: ignore[arg-type]


def test_todo_constructor_rejects_int_as_text() -> None:
    """Todo(id=1, text=123) should raise ValueError."""
    with pytest.raises(ValueError, match="'text' must be a string"):
        Todo(id=1, text=123)  # type: ignore[arg-type]


def test_todo_constructor_rejects_list_as_text() -> None:
    """Todo(id=1, text=['list']) should raise ValueError."""
    with pytest.raises(ValueError, match="'text' must be a string"):
        Todo(id=1, text=["not a string"])  # type: ignore[arg-type]


def test_todo_constructor_accepts_valid_string() -> None:
    """Todo(id=1, text='valid') should work as before."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"
    assert todo.id == 1


def test_todo_constructor_accepts_empty_string() -> None:
    """Todo(id=1, text='') should be accepted (empty string is still a string)."""
    todo = Todo(id=1, text="")
    assert todo.text == ""
