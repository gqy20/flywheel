"""Tests for Todo constructor text validation (Issue #6786).

These tests verify that:
1. Todo constructor rejects empty string text
2. Todo constructor rejects whitespace-only text
3. Todo constructor accepts valid text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Todo(id=1, text="") should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only_string() -> None:
    """Todo(id=1, text="   ") should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_constructor_rejects_tabs_and_newlines_only() -> None:
    """Todo(id=1, text="\\t\\n") should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_accepts_valid_text() -> None:
    """Todo(id=1, text="valid") should work normally."""
    todo = Todo(id=1, text="valid")
    assert todo.text == "valid"
    assert todo.id == 1
    assert todo.done is False


def test_todo_constructor_accepts_text_with_leading_trailing_spaces() -> None:
    """Todo constructor should accept text that becomes valid after strip.

    Note: Unlike rename(), the constructor does not auto-strip text,
    but it should reject text that is only whitespace.
    """
    todo = Todo(id=1, text="  valid text  ")
    assert todo.text == "  valid text  "


def test_todo_constructor_validation_consistency_with_rename() -> None:
    """Todo constructor validation should be consistent with rename()."""
    # Both should raise the same error for empty text
    empty_error = None
    try:
        Todo(id=1, text="")
    except ValueError as e:
        empty_error = str(e)

    todo = Todo(id=1, text="valid")
    rename_error = None
    try:
        todo.rename("")
    except ValueError as e:
        rename_error = str(e)

    assert empty_error == rename_error
    assert "cannot be empty" in empty_error
