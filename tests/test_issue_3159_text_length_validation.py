"""Tests for text length validation (Issue #3159).

These tests verify that:
1. Todo with text > 1000 chars raises ValueError in __post_init__
2. rename() with text > 1000 chars raises ValueError
3. from_dict() validates text length and raises clear error
4. Error messages include actual length and max allowed
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


def test_todo_rejects_text_exceeding_max_length() -> None:
    """Todo.__post_init__ should raise ValueError if text exceeds MAX_TEXT_LENGTH."""
    # Create text that is exactly at the limit
    max_text = "a" * MAX_TEXT_LENGTH
    # This should succeed
    todo = Todo(id=1, text=max_text)
    assert len(todo.text) == MAX_TEXT_LENGTH

    # Create text that exceeds the limit
    too_long_text = "a" * (MAX_TEXT_LENGTH + 1)
    # This should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text=too_long_text)

    # Error message should include actual length and max allowed
    error_msg = str(exc_info.value)
    assert str(MAX_TEXT_LENGTH + 1) in error_msg
    assert str(MAX_TEXT_LENGTH) in error_msg


def test_todo_rename_rejects_text_exceeding_max_length() -> None:
    """Todo.rename() should raise ValueError if text exceeds MAX_TEXT_LENGTH."""
    # Create a valid todo first
    todo = Todo(id=1, text="initial text")

    # Create text that is exactly at the limit
    max_text = "b" * MAX_TEXT_LENGTH
    # This should succeed
    todo.rename(max_text)
    assert len(todo.text) == MAX_TEXT_LENGTH

    # Create text that exceeds the limit
    too_long_text = "b" * (MAX_TEXT_LENGTH + 1)
    # This should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        todo.rename(too_long_text)

    # Error message should include actual length and max allowed
    error_msg = str(exc_info.value)
    assert str(MAX_TEXT_LENGTH + 1) in error_msg
    assert str(MAX_TEXT_LENGTH) in error_msg


def test_from_dict_rejects_text_exceeding_max_length() -> None:
    """Todo.from_dict() should validate text length and raise clear error."""
    # Create a valid todo using from_dict
    valid_data = {"id": 1, "text": "valid text", "done": False}
    todo = Todo.from_dict(valid_data)
    assert todo.text == "valid text"

    # Create text that exceeds the limit
    too_long_text = "c" * (MAX_TEXT_LENGTH + 1)
    invalid_data = {"id": 1, "text": too_long_text, "done": False}

    # This should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict(invalid_data)

    # Error message should include actual length and max allowed
    error_msg = str(exc_info.value)
    assert str(MAX_TEXT_LENGTH + 1) in error_msg
    assert str(MAX_TEXT_LENGTH) in error_msg


def test_max_text_length_is_reasonable() -> None:
    """MAX_TEXT_LENGTH should be a reasonable value (e.g., 1000 chars)."""
    # MAX_TEXT_LENGTH should be defined and reasonable
    assert MAX_TEXT_LENGTH == 1000, "MAX_TEXT_LENGTH should be 1000 characters"


def test_todo_accepts_text_at_exactly_max_length() -> None:
    """Todo should accept text that is exactly at MAX_TEXT_LENGTH."""
    exact_length_text = "x" * MAX_TEXT_LENGTH
    todo = Todo(id=1, text=exact_length_text)
    assert todo.text == exact_length_text
    assert len(todo.text) == MAX_TEXT_LENGTH
