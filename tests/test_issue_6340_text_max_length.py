"""Tests for Todo text maximum length validation (Issue #6340).

These tests verify that:
1. Todo text cannot exceed MAX_TEXT_LENGTH (1000 chars)
2. Creating a Todo with text > MAX_TEXT_LENGTH raises ValueError
3. Renaming a Todo with text > MAX_TEXT_LENGTH raises ValueError
4. Error messages clearly indicate the maximum allowed length
5. Boundary values (exactly MAX_TEXT_LENGTH) work correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


def test_max_text_length_constant() -> None:
    """MAX_TEXT_LENGTH should be 1000 characters."""
    assert MAX_TEXT_LENGTH == 1000


def test_todo_create_with_exact_max_length() -> None:
    """Todo with text exactly at MAX_TEXT_LENGTH should succeed."""
    text = "a" * MAX_TEXT_LENGTH
    todo = Todo(id=1, text=text)
    assert len(todo.text) == MAX_TEXT_LENGTH


def test_todo_create_exceeds_max_length() -> None:
    """Todo with text exceeding MAX_TEXT_LENGTH should raise ValueError."""
    text = "a" * (MAX_TEXT_LENGTH + 1)
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text=text)

    # Error message should mention max length
    error_msg = str(exc_info.value)
    assert "1000" in error_msg or "MAX_TEXT_LENGTH" in error_msg


def test_todo_rename_with_exact_max_length() -> None:
    """Renaming to text exactly at MAX_TEXT_LENGTH should succeed."""
    todo = Todo(id=1, text="original")
    text = "b" * MAX_TEXT_LENGTH
    todo.rename(text)
    assert len(todo.text) == MAX_TEXT_LENGTH


def test_todo_rename_exceeds_max_length() -> None:
    """Renaming to text exceeding MAX_TEXT_LENGTH should raise ValueError."""
    todo = Todo(id=1, text="original")
    text = "c" * (MAX_TEXT_LENGTH + 1)
    with pytest.raises(ValueError) as exc_info:
        todo.rename(text)

    # Error message should mention max length
    error_msg = str(exc_info.value)
    assert "1000" in error_msg or "MAX_TEXT_LENGTH" in error_msg


def test_todo_create_with_very_long_text() -> None:
    """Todo with excessively long text (10001 chars) should raise ValueError."""
    text = "x" * 10001
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text=text)

    error_msg = str(exc_info.value)
    assert "1000" in error_msg or "MAX_TEXT_LENGTH" in error_msg


def test_todo_rename_with_very_long_text() -> None:
    """Renaming to excessively long text (10001 chars) should raise ValueError."""
    todo = Todo(id=1, text="original")
    text = "y" * 10001
    with pytest.raises(ValueError) as exc_info:
        todo.rename(text)

    error_msg = str(exc_info.value)
    assert "1000" in error_msg or "MAX_TEXT_LENGTH" in error_msg
