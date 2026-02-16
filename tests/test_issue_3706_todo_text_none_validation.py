"""Tests for Todo text field validation (Issue #3706).

These tests verify that:
1. Todo rejects None for text field with clear error
2. repr(Todo) works correctly for valid todos
3. from_dict continues to validate text type correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_none_for_text() -> None:
    """Todo(id=1, text=None) should raise TypeError or ValueError."""
    with pytest.raises((TypeError, ValueError)) as exc_info:
        Todo(id=1, text=None)  # type: ignore[arg-type]

    error_msg = str(exc_info.value)
    assert "text" in error_msg.lower()


def test_todo_repr_works_for_valid_todo() -> None:
    """repr(Todo) should work correctly when text is valid."""
    todo = Todo(id=1, text="valid text")
    result = repr(todo)

    assert "Todo" in result
    assert "id=1" in result
    assert "valid text" in result


def test_todo_from_dict_rejects_none_text() -> None:
    """from_dict should still reject None for text."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": 1, "text": None})

    error_msg = str(exc_info.value)
    assert "text" in error_msg.lower()


def test_todo_init_accepts_valid_string_text() -> None:
    """Todo should accept valid string for text."""
    todo = Todo(id=1, text="a valid todo item")
    assert todo.text == "a valid todo item"
