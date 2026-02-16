"""Tests for Todo text length validation (Issue #3820).

These tests verify that:
1. Todo text is limited to MAX_TEXT_LENGTH characters (1000)
2. Validation applies at construction, rename, and from_dict
3. Error messages clearly indicate the maximum allowed length
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


def test_todo_text_exceeds_max_length_raises() -> None:
    """Todo() with text > MAX_TEXT_LENGTH should raise ValueError."""
    long_text = "a" * (MAX_TEXT_LENGTH + 1)

    with pytest.raises(ValueError, match="exceeds maximum length"):
        Todo(id=1, text=long_text)


def test_todo_rename_exceeds_max_length_raises() -> None:
    """Todo.rename() with text > MAX_TEXT_LENGTH should raise ValueError."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at
    long_text = "b" * (MAX_TEXT_LENGTH + 1)

    with pytest.raises(ValueError, match="exceeds maximum length"):
        todo.rename(long_text)

    # Verify state unchanged after failed validation
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_todo_text_at_max_length_accepts() -> None:
    """Todo() with text exactly MAX_TEXT_LENGTH should be accepted."""
    max_text = "x" * MAX_TEXT_LENGTH
    todo = Todo(id=1, text=max_text)

    assert todo.text == max_text
    assert len(todo.text) == MAX_TEXT_LENGTH


def test_todo_rename_at_max_length_accepts() -> None:
    """Todo.rename() with text exactly MAX_TEXT_LENGTH should be accepted."""
    todo = Todo(id=1, text="original")
    max_text = "y" * MAX_TEXT_LENGTH

    todo.rename(max_text)

    assert todo.text == max_text
    assert len(todo.text) == MAX_TEXT_LENGTH


def test_todo_from_dict_exceeds_max_length_raises() -> None:
    """Todo.from_dict() with text > MAX_TEXT_LENGTH should raise ValueError."""
    long_text = "c" * (MAX_TEXT_LENGTH + 1)
    data = {"id": 1, "text": long_text}

    with pytest.raises(ValueError, match="exceeds maximum length"):
        Todo.from_dict(data)


def test_todo_from_dict_at_max_length_accepts() -> None:
    """Todo.from_dict() with text exactly MAX_TEXT_LENGTH should be accepted."""
    max_text = "z" * MAX_TEXT_LENGTH
    data = {"id": 1, "text": max_text}

    todo = Todo.from_dict(data)

    assert todo.text == max_text
    assert len(todo.text) == MAX_TEXT_LENGTH


def test_error_message_includes_max_length() -> None:
    """Error message should clearly indicate the maximum allowed length."""
    long_text = "a" * 2000

    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text=long_text)

    error_msg = str(exc_info.value)
    assert str(MAX_TEXT_LENGTH) in error_msg


def test_rename_validates_after_stripping_whitespace() -> None:
    """Rename validation should apply after stripping whitespace."""
    todo = Todo(id=1, text="original")
    # Text that exceeds limit after stripping leading/trailing whitespace
    long_text = "  " + "a" * (MAX_TEXT_LENGTH + 1) + "  "

    with pytest.raises(ValueError, match="exceeds maximum length"):
        todo.rename(long_text)
