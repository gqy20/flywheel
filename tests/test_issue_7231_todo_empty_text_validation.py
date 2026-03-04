"""Tests for Todo empty text validation (Issue #7231).

These tests verify that Todo.__post_init__ validates text field
to reject empty strings and whitespace-only strings, matching the
validation in rename() and TodoApp.add().
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_rejects_empty_string_text() -> None:
    """Todo should reject empty string for text field."""
    with pytest.raises(ValueError, match=r"text cannot be empty"):
        Todo(id=1, text="")


def test_todo_rejects_whitespace_only_text() -> None:
    """Todo should reject whitespace-only string for text field."""
    with pytest.raises(ValueError, match=r"text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_rejects_whitespace_only_text_with_tabs() -> None:
    """Todo should reject whitespace-only string with tabs/newlines."""
    with pytest.raises(ValueError, match=r"text cannot be empty"):
        Todo(id=1, text="\t\n  ")


def test_todo_accepts_valid_text() -> None:
    """Todo should accept valid non-empty text."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"


def test_todo_accepts_text_with_leading_trailing_spaces() -> None:
    """Todo should accept text with meaningful content after stripping spaces."""
    todo = Todo(id=1, text="  valid text  ")
    # The text should be stripped and validated in __post_init__
    assert todo.text == "valid text"


def test_todo_strips_whitespace_from_valid_text() -> None:
    """Todo should strip leading/trailing whitespace from valid text."""
    todo = Todo(id=1, text="\tvalid text\n")
    assert todo.text == "valid text"
