"""Tests for Todo.__init__ whitespace handling (Issue #7107).

These tests verify that Todo.__init__ strips and validates the 'text' parameter
at construction time, making it consistent with rename() and cli.add().

Acceptance criteria:
- Todo(id=1, text=' valid ') stores text as 'valid' (stripped)
- Todo(id=1, text='') raises ValueError
- Todo(id=1, text=' ') raises ValueError
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_strips_whitespace_from_text() -> None:
    """Todo.__init__ should strip leading/trailing whitespace from text."""
    todo = Todo(id=1, text=" padded ")
    assert todo.text == "padded"


def test_todo_init_strips_tabs_and_newlines() -> None:
    """Todo.__init__ should strip tabs and newlines from text."""
    todo = Todo(id=1, text="\ttext with whitespace\n")
    assert todo.text == "text with whitespace"


def test_todo_init_raises_value_error_on_empty_text() -> None:
    """Todo.__init__ should raise ValueError when text is empty string."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_raises_value_error_on_whitespace_only_text() -> None:
    """Todo.__init__ should raise ValueError when text contains only whitespace."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_init_raises_value_error_on_tabs_and_newlines_only() -> None:
    """Todo.__init__ should raise ValueError when text contains only tabs/newlines."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_init_behavior_matches_rename() -> None:
    """Todo.__init__ should be consistent with rename() method behavior."""
    # Both should strip whitespace
    todo1 = Todo(id=1, text="  test  ")
    todo2 = Todo(id=2, text="original")
    todo2.rename("  test  ")

    # Both should have the same stripped text
    assert todo1.text == todo2.text
