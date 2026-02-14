"""Tests for issue #3323: Add text length validation to Todo.rename() and constructor."""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


def test_todo_rename_rejects_text_exceeding_max_length() -> None:
    """Issue #3323: Todo.rename() should reject text exceeding MAX_TEXT_LENGTH."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    # Text exceeding MAX_TEXT_LENGTH should raise ValueError
    long_text = "x" * (MAX_TEXT_LENGTH + 1)
    with pytest.raises(ValueError, match=f"exceeds maximum.*{MAX_TEXT_LENGTH}"):
        todo.rename(long_text)

    # Verify state unchanged after failed validation
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_todo_from_dict_rejects_text_exceeding_max_length() -> None:
    """Issue #3323: Todo.from_dict() should reject text exceeding MAX_TEXT_LENGTH."""
    long_text = "x" * (MAX_TEXT_LENGTH + 1)
    data = {"id": 1, "text": long_text}

    with pytest.raises(ValueError, match=f"exceeds maximum.*{MAX_TEXT_LENGTH}"):
        Todo.from_dict(data)


def test_todo_rename_accepts_text_at_max_length() -> None:
    """Issue #3323: Todo.rename() should accept text at exactly MAX_TEXT_LENGTH."""
    todo = Todo(id=1, text="original")

    # Text at exactly MAX_TEXT_LENGTH should succeed
    max_text = "x" * MAX_TEXT_LENGTH
    todo.rename(max_text)
    assert todo.text == max_text


def test_todo_from_dict_accepts_text_at_max_length() -> None:
    """Issue #3323: Todo.from_dict() should accept text at exactly MAX_TEXT_LENGTH."""
    max_text = "x" * MAX_TEXT_LENGTH
    data = {"id": 1, "text": max_text}

    todo = Todo.from_dict(data)
    assert todo.text == max_text


def test_max_text_length_is_500() -> None:
    """Issue #3323: MAX_TEXT_LENGTH should be 500 characters."""
    assert MAX_TEXT_LENGTH == 500
