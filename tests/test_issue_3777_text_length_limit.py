"""Regression tests for Issue #3777: Todo text length limit.

This test file ensures that todo text fields have a maximum length limit
to prevent potential memory exhaustion attacks.
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


def test_max_text_length_constant_exists() -> None:
    """MAX_TEXT_LENGTH constant should be defined and reasonable."""
    assert MAX_TEXT_LENGTH > 0
    assert MAX_TEXT_LENGTH <= 1_000_000  # Sanity check: should not exceed 1MB of text


def test_todo_constructor_rejects_text_exceeding_max_length() -> None:
    """Todo constructor with text > MAX_TEXT_LENGTH should raise ValueError."""
    long_text = "a" * (MAX_TEXT_LENGTH + 1)
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text=long_text)
    assert "maximum" in str(exc_info.value).lower()
    assert str(MAX_TEXT_LENGTH) in str(exc_info.value)


def test_todo_rename_rejects_text_exceeding_max_length() -> None:
    """Todo.rename() with text > MAX_TEXT_LENGTH should raise ValueError."""
    todo = Todo(id=1, text="Valid text")
    long_text = "a" * (MAX_TEXT_LENGTH + 1)
    with pytest.raises(ValueError) as exc_info:
        todo.rename(long_text)
    assert "maximum" in str(exc_info.value).lower()
    assert str(MAX_TEXT_LENGTH) in str(exc_info.value)


def test_todo_constructor_accepts_text_at_max_length() -> None:
    """Todo constructor with text exactly at MAX_TEXT_LENGTH should succeed."""
    text_at_limit = "a" * MAX_TEXT_LENGTH
    todo = Todo(id=1, text=text_at_limit)
    assert len(todo.text) == MAX_TEXT_LENGTH


def test_todo_rename_accepts_text_at_max_length() -> None:
    """Todo.rename() with text exactly at MAX_TEXT_LENGTH should succeed."""
    todo = Todo(id=1, text="Original text")
    text_at_limit = "b" * MAX_TEXT_LENGTH
    todo.rename(text_at_limit)
    assert len(todo.text) == MAX_TEXT_LENGTH


def test_todo_from_dict_rejects_text_exceeding_max_length() -> None:
    """Todo.from_dict() with text > MAX_TEXT_LENGTH should raise ValueError."""
    long_text = "a" * (MAX_TEXT_LENGTH + 1)
    data = {"id": 1, "text": long_text}
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict(data)
    assert "maximum" in str(exc_info.value).lower()
    assert str(MAX_TEXT_LENGTH) in str(exc_info.value)


def test_todo_from_dict_accepts_text_at_max_length() -> None:
    """Todo.from_dict() with text exactly at MAX_TEXT_LENGTH should succeed."""
    text_at_limit = "a" * MAX_TEXT_LENGTH
    data = {"id": 1, "text": text_at_limit}
    todo = Todo.from_dict(data)
    assert len(todo.text) == MAX_TEXT_LENGTH
