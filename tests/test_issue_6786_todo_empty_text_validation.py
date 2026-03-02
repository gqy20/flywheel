"""Tests for Todo constructor text validation (Issue #6786).

These tests verify that the Todo constructor validates text content
to be consistent with rename() and add() methods.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_empty_string_raises_value_error() -> None:
    """Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_whitespace_only_raises_value_error() -> None:
    """Todo(id=1, text='   ') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_constructor_valid_text_succeeds() -> None:
    """Todo(id=1, text='valid') should work normally."""
    todo = Todo(id=1, text="valid")
    assert todo.text == "valid"
    assert todo.id == 1


def test_todo_constructor_text_with_whitespace_is_stripped() -> None:
    """Todo constructor should strip whitespace from text like rename()."""
    todo = Todo(id=1, text="  valid text  ")
    assert todo.text == "valid text"
