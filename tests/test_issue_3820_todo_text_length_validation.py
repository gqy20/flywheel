"""Tests for Todo text length validation (Issue #3820).

These tests verify that:
1. Todo creation with text exceeding MAX_TEXT_LENGTH raises ValueError
2. Todo.rename() with text exceeding MAX_TEXT_LENGTH raises ValueError
3. Text at exactly MAX_TEXT_LENGTH is accepted
4. Error message clearly indicates the maximum allowed length
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_text_exceeds_max_length_raises() -> None:
    """Todo(text='a'*10000) should raise ValueError."""
    long_text = "a" * 10000
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text=long_text)
    # Error message should indicate maximum allowed length
    assert "1000" in str(exc_info.value)


def test_todo_rename_exceeds_max_length_raises() -> None:
    """todo.rename('a'*10000) should raise ValueError."""
    todo = Todo(id=1, text="initial text")
    long_text = "a" * 10000
    with pytest.raises(ValueError) as exc_info:
        todo.rename(long_text)
    # Error message should indicate maximum allowed length
    assert "1000" in str(exc_info.value)


def test_todo_text_at_max_length_accepts() -> None:
    """Todo with text at exactly MAX_TEXT_LENGTH (1000 chars) should be accepted."""
    # MAX_TEXT_LENGTH is 1000 characters
    max_length_text = "a" * 1000
    todo = Todo(id=1, text=max_length_text)
    assert todo.text == max_length_text


def test_todo_rename_at_max_length_accepts() -> None:
    """rename() with text at exactly MAX_TEXT_LENGTH should be accepted."""
    todo = Todo(id=1, text="initial text")
    max_length_text = "b" * 1000
    todo.rename(max_length_text)
    assert todo.text == max_length_text


def test_todo_text_just_over_max_length_raises() -> None:
    """Todo with text one char over MAX_TEXT_LENGTH should raise ValueError."""
    over_limit_text = "a" * 1001
    with pytest.raises(ValueError):
        Todo(id=1, text=over_limit_text)


def test_todo_rename_just_over_max_length_raises() -> None:
    """rename() with text one char over MAX_TEXT_LENGTH should raise ValueError."""
    todo = Todo(id=1, text="initial text")
    over_limit_text = "a" * 1001
    with pytest.raises(ValueError):
        todo.rename(over_limit_text)
