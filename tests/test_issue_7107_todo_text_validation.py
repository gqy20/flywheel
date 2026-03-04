"""Tests for Todo.__init__ text whitespace validation (Issue #7107).

These tests verify that:
1. Todo.__init__ strips whitespace from text at construction time
2. Todo.__init__ raises ValueError for empty text after stripping
3. Behavior is consistent with rename() method and cli.add()
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_strips_whitespace_from_text() -> None:
    """Todo.__init__ should strip leading/trailing whitespace from text."""
    todo = Todo(id=1, text=" valid ")
    assert todo.text == "valid"


def test_todo_init_strips_whitespace_various_types() -> None:
    """Todo.__init__ should strip various whitespace characters (spaces, tabs, newlines)."""
    todo = Todo(id=1, text="\t\n  padded  \n\t")
    assert todo.text == "padded"


def test_todo_init_raises_for_empty_text() -> None:
    """Todo.__init__ should raise ValueError for empty text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_raises_for_whitespace_only_text() -> None:
    """Todo.__init__ should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_init_raises_for_tabs_and_newlines_only() -> None:
    """Todo.__init__ should raise ValueError for text with only tabs/newlines."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_init_consistent_with_rename() -> None:
    """Todo.__init__ behavior should be consistent with rename() method."""
    # Both should strip and store stripped text
    todo = Todo(id=1, text=" original ")
    assert todo.text == "original"

    todo.rename(" renamed ")
    assert todo.text == "renamed"
