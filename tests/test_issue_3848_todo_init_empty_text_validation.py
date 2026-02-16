"""Tests for Todo.__init__ empty text validation (Issue #3848).

These tests verify that:
1. Todo.__init__ rejects empty text (consistent with Todo.rename and TodoApp.add)
2. Todo.__init__ rejects whitespace-only text
3. Error message is clear and consistent with other validation errors
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_empty_text() -> None:
    """Todo.__init__ should reject empty text string."""
    with pytest.raises(ValueError, match=r"text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_rejects_whitespace_only_text() -> None:
    """Todo.__init__ should reject whitespace-only text (consistent with rename/add)."""
    with pytest.raises(ValueError, match=r"text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_init_rejects_tab_only_text() -> None:
    """Todo.__init__ should reject tab-only text."""
    with pytest.raises(ValueError, match=r"text cannot be empty"):
        Todo(id=1, text="\t")


def test_todo_init_rejects_newline_only_text() -> None:
    """Todo.__init__ should reject newline-only text."""
    with pytest.raises(ValueError, match=r"text cannot be empty"):
        Todo(id=1, text="\n")


def test_todo_init_accepts_text_with_leading_trailing_spaces() -> None:
    """Todo.__init__ should accept text that becomes non-empty after stripping."""
    # Text with leading/trailing spaces should be accepted (and stripped)
    todo = Todo(id=1, text="  valid text  ")
    # The fix should strip the text, making it "valid text"
    assert todo.text == "valid text"


def test_todo_init_validation_consistent_with_rename() -> None:
    """Todo.__init__ should have same validation behavior as Todo.rename()."""
    # rename() rejects empty text
    todo = Todo(id=1, text="original")
    with pytest.raises(ValueError, match=r"text cannot be empty"):
        todo.rename("")

    # __init__ should also reject empty text
    with pytest.raises(ValueError, match=r"text cannot be empty"):
        Todo(id=1, text="")
