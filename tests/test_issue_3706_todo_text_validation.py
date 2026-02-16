"""Tests for Todo text field validation (Issue #3706).

These tests verify that:
1. Todo.__init__ rejects None for text field
2. Todo.__repr__ works correctly for valid text
3. from_dict continues to validate text type correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_none_for_text() -> None:
    """Todo.__init__ should raise TypeError when text is None."""
    with pytest.raises(TypeError) as exc_info:
        Todo(id=1, text=None)  # type: ignore[arg-type]

    # Error message should be clear
    error_msg = str(exc_info.value)
    assert "text" in error_msg.lower()


def test_todo_repr_works_with_valid_text() -> None:
    """repr(Todo) should work correctly when text is a valid string."""
    todo = Todo(id=1, text="valid text")
    result = repr(todo)

    assert "Todo" in result
    assert "id=1" in result
    assert "valid text" in result


def test_todo_from_dict_still_validates_text_type() -> None:
    """from_dict should continue to reject non-string text."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": 1, "text": None})  # type: ignore[dict-item]

    error_msg = str(exc_info.value)
    assert "text" in error_msg.lower()
    assert "string" in error_msg.lower()


def test_todo_init_rejects_empty_string() -> None:
    """Todo.__init__ should raise ValueError when text is empty string."""
    # Empty strings should also be rejected as per rename() behavior
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="")

    error_msg = str(exc_info.value)
    assert "text" in error_msg.lower()
    assert "empty" in error_msg.lower()
