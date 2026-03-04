"""Tests for Todo.__init__ text type validation (Issue #7105).

These tests verify that Todo validates the 'text' parameter type at
construction time, not just in from_dict().
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_non_string_text_int() -> None:
    """Todo(id=1, text=123) should raise ValueError."""
    with pytest.raises(ValueError, match="'text' must be a string"):
        Todo(id=1, text=123)


def test_todo_init_rejects_non_string_text_none() -> None:
    """Todo(id=1, text=None) should raise ValueError."""
    with pytest.raises(ValueError, match="'text' must be a string"):
        Todo(id=1, text=None)


def test_todo_init_rejects_non_string_text_list() -> None:
    """Todo(id=1, text=['list']) should raise ValueError."""
    with pytest.raises(ValueError, match="'text' must be a string"):
        Todo(id=1, text=["list"])


def test_todo_init_accepts_valid_string_text() -> None:
    """Todo(id=1, text='valid string') should succeed."""
    todo = Todo(id=1, text="valid string")
    assert todo.text == "valid string"
    assert todo.id == 1


def test_todo_init_accepts_empty_string_text() -> None:
    """Todo(id=1, text='') should succeed (empty string is still a string)."""
    todo = Todo(id=1, text="")
    assert todo.text == ""
