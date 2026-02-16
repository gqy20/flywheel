"""Tests for Todo.__init__ text validation (Issue #3848).

These tests verify that:
1. Todo.__init__ validates text is non-empty (consistent with rename() and TodoApp.add())
2. Empty string text raises ValueError
3. Whitespace-only text raises ValueError
4. Valid text works normally
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_empty_string_raises_value_error() -> None:
    """Todo.__init__ should raise ValueError for empty text."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="")
    assert "cannot be empty" in str(exc_info.value)


def test_todo_init_whitespace_only_raises_value_error() -> None:
    """Todo.__init__ should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="   ")
    assert "cannot be empty" in str(exc_info.value)


def test_todo_init_whitespace_only_with_tabs_raises_value_error() -> None:
    """Todo.__init__ should raise ValueError for tabs/whitespace-only text."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="\t\n ")
    assert "cannot be empty" in str(exc_info.value)


def test_todo_init_valid_text_still_works() -> None:
    """Todo.__init__ should work normally with valid text."""
    todo = Todo(id=1, text="valid todo text")
    assert todo.text == "valid todo text"


def test_todo_init_text_with_leading_trailing_spaces_preserved() -> None:
    """Todo.__init__ should strip and validate but this behavior matches rename()."""
    # Note: The fix should strip text similar to rename() method
    # Since rename() does text = text.strip() before validation,
    # we follow the same pattern for consistency
    todo = Todo(id=1, text="  valid text  ")
    assert todo.text == "valid text"


def test_todo_init_error_message_matches_rename() -> None:
    """Todo.__init__ error message should match rename() method."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="")
    # Error message should match: "Todo text cannot be empty"
    assert "Todo text cannot be empty" in str(exc_info.value)
