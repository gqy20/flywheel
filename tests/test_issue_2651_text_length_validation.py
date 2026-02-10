"""Tests for text field length validation (Issue #2651).

These tests verify that:
1. Todo.from_dict rejects text fields exceeding MAX_TODO_TEXT_LENGTH
2. Error message includes the max length and actual length
3. Normal length text is accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo

# Define the maximum text length - must match todo.py
_MAX_TODO_TEXT_LENGTH = 100_000  # 100KB max per todo text


def test_todo_from_dict_rejects_excessively_long_text() -> None:
    """Todo.from_dict should reject text fields exceeding MAX_TODO_TEXT_LENGTH."""
    # Create a text that exceeds the limit (100KB + 1 char)
    long_text = "x" * (_MAX_TODO_TEXT_LENGTH + 1)

    with pytest.raises(ValueError, match=r"Text.*too long|max.*length|characters"):
        Todo.from_dict({"id": 1, "text": long_text})


def test_todo_from_dict_rejects_1mb_text() -> None:
    """Todo.from_dict should reject 1MB text strings to prevent DoS."""
    # Create a 1MB text string
    huge_text = "a" * (1_000_000)

    with pytest.raises(ValueError, match=r"Text.*too long|max.*length|characters"):
        Todo.from_dict({"id": 1, "text": huge_text})


def test_todo_from_dict_error_includes_lengths() -> None:
    """Error message should include both actual length and max limit."""
    long_text = "y" * (_MAX_TODO_TEXT_LENGTH + 100)

    try:
        Todo.from_dict({"id": 1, "text": long_text})
        pytest.fail("Expected ValueError for excessively long text")
    except ValueError as e:
        error_msg = str(e).lower()
        # Error should mention the length limit or that it's too long
        assert "text" in error_msg or "length" in error_msg


def test_todo_from_dict_accepts_normal_text() -> None:
    """Todo.from_dict should accept normal length text strings."""
    # Test with a reasonable length (100 chars)
    normal_text = "This is a normal length todo item " * 5

    todo = Todo.from_dict({"id": 1, "text": normal_text})
    assert todo.text == normal_text


def test_todo_from_dict_accepts_max_length_text() -> None:
    """Todo.from_dict should accept text exactly at the max length."""
    max_text = "z" * _MAX_TODO_TEXT_LENGTH

    todo = Todo.from_dict({"id": 1, "text": max_text})
    assert todo.text == max_text
    assert len(todo.text) == _MAX_TODO_TEXT_LENGTH


def test_todo_from_dict_accepts_near_max_text() -> None:
    """Todo.from_dict should accept text close to but under the max length."""
    near_max_text = "w" * (_MAX_TODO_TEXT_LENGTH - 1)

    todo = Todo.from_dict({"id": 1, "text": near_max_text})
    assert todo.text == near_max_text


def test_todo_rename_validates_length() -> None:
    """Todo.rename should also validate text length."""
    # Create a valid todo first
    todo = Todo(id=1, text="original")

    # Try to rename to excessively long text
    long_text = "x" * (_MAX_TODO_TEXT_LENGTH + 1)

    with pytest.raises(ValueError, match=r"Text.*too long|max.*length|characters"):
        todo.rename(long_text)
