"""Tests for Todo constructor empty text validation (Issue #5444).

These tests verify that Todo constructor rejects empty or whitespace-only text,
matching the validation already present in rename() method.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Bug #5444: Todo constructor should reject empty strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Bug #5444: Todo constructor should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Bug #5444: Todo constructor should accept valid non-empty text."""
    todo = Todo(id=1, text="valid")
    assert todo.text == "valid"


def test_todo_constructor_strips_whitespace_and_accepts() -> None:
    """Bug #5444: Todo constructor should strip whitespace and accept if non-empty."""
    todo = Todo(id=1, text="  valid  ")
    assert todo.text == "valid"
