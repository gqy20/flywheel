"""Tests for Todo.__post_init__ text validation (Issue #3334).

These tests verify that:
1. Todo construction with empty text raises ValueError
2. Todo construction with whitespace-only text raises ValueError
3. Todo construction with valid text still works
4. Error message is consistent with rename() method behavior
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_empty_text_raises_value_error() -> None:
    """Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="")
    assert "Todo text cannot be empty" in str(exc_info.value)


def test_todo_whitespace_only_text_raises_value_error() -> None:
    """Todo(id=1, text='   ') should raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="   ")
    assert "Todo text cannot be empty" in str(exc_info.value)


def test_todo_tab_newline_whitespace_raises_value_error() -> None:
    """Todo(id=1, text='  \\t\\n  ') should raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="  \t\n  ")
    assert "Todo text cannot be empty" in str(exc_info.value)


def test_todo_valid_text_still_works() -> None:
    """Todo(id=1, text='valid') should still work."""
    todo = Todo(id=1, text="valid")
    assert todo.text == "valid"
    assert todo.id == 1
    assert todo.done is False


def test_todo_text_with_leading_trailing_whitespace_works() -> None:
    """Todo with text that has content but also whitespace should work."""
    todo = Todo(id=1, text="  valid text  ")
    # Note: unlike rename(), __post_init__ should not strip - just validate non-empty
    assert todo.text == "  valid text  "


def test_todo_from_dict_empty_text_raises_value_error() -> None:
    """Todo.from_dict with empty text should also raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": 1, "text": ""})
    assert "Todo text cannot be empty" in str(exc_info.value)


def test_todo_from_dict_whitespace_text_raises_value_error() -> None:
    """Todo.from_dict with whitespace-only text should also raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": 1, "text": "   "})
    assert "Todo text cannot be empty" in str(exc_info.value)
