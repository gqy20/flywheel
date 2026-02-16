"""Tests for Todo text field validation (Issue #3706).

These tests verify that:
1. Todo.__init__ rejects None for text field
2. Todo.__init__ rejects non-string values for text field
3. repr(Todo) works correctly for valid todos
4. from_dict continues to validate text type correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_none_for_text() -> None:
    """Todo(id=1, text=None) should raise TypeError or ValueError."""
    with pytest.raises((TypeError, ValueError)) as exc_info:
        Todo(id=1, text=None)  # type: ignore[arg-type]

    # Error message should be clear about the issue
    error_msg = str(exc_info.value)
    assert "text" in error_msg.lower()
    assert "none" in error_msg.lower() or "str" in error_msg.lower() or "string" in error_msg.lower()


def test_todo_init_rejects_non_string_text() -> None:
    """Todo.__init__ should reject non-string values for text field."""
    with pytest.raises((TypeError, ValueError)):
        Todo(id=1, text=123)  # type: ignore[arg-type]

    with pytest.raises((TypeError, ValueError)):
        Todo(id=1, text=["list", "of", "strings"])  # type: ignore[arg-type]

    with pytest.raises((TypeError, ValueError)):
        Todo(id=1, text={"key": "value"})  # type: ignore[arg-type]


def test_todo_repr_with_valid_text_works() -> None:
    """repr(Todo) should work correctly when text is a valid string."""
    todo = Todo(id=1, text="valid task")
    result = repr(todo)

    assert "Todo" in result
    assert "id=1" in result
    assert "valid task" in result


def test_todo_from_dict_still_validates_text_type() -> None:
    """from_dict should continue to validate text type correctly."""
    # from_dict should reject None
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": 1, "text": None})

    assert "text" in str(exc_info.value).lower()

    # from_dict should reject non-string
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": 1, "text": 123})

    assert "text" in str(exc_info.value).lower()

    # from_dict should accept valid strings
    todo = Todo.from_dict({"id": 1, "text": "valid"})
    assert todo.text == "valid"
