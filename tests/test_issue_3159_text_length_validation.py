"""Tests for Todo text length validation (Issue #3159).

These tests verify that:
1. Todo with text > 1000 chars raises ValueError in __post_init__
2. rename() with text > 1000 chars raises ValueError
3. from_dict() validates text length and raises clear error
4. Error messages include actual length and max allowed
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_rejects_text_exceeding_max_length() -> None:
    """Todo with text > 1000 chars should raise ValueError."""
    long_text = "a" * 1001
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text=long_text)

    assert "exceeds maximum length" in str(exc_info.value).lower()
    assert "1001" in str(exc_info.value)
    assert "1000" in str(exc_info.value)


def test_todo_accepts_text_at_max_length() -> None:
    """Todo with text == 1000 chars should be accepted."""
    max_text = "a" * 1000
    todo = Todo(id=1, text=max_text)
    assert todo.text == max_text


def test_todo_rename_rejects_text_exceeding_max_length() -> None:
    """rename() with text > 1000 chars should raise ValueError."""
    todo = Todo(id=1, text="original text")
    long_text = "b" * 1001

    with pytest.raises(ValueError) as exc_info:
        todo.rename(long_text)

    assert "exceeds maximum length" in str(exc_info.value).lower()
    assert "1001" in str(exc_info.value)
    assert "1000" in str(exc_info.value)


def test_todo_rename_accepts_text_at_max_length() -> None:
    """rename() with text == 1000 chars should be accepted."""
    todo = Todo(id=1, text="original text")
    max_text = "c" * 1000
    todo.rename(max_text)
    assert todo.text == max_text


def test_from_dict_rejects_text_exceeding_max_length() -> None:
    """from_dict() should validate text length and raise clear error."""
    long_text = "d" * 1001
    data = {"id": 1, "text": long_text}

    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict(data)

    assert "exceeds maximum length" in str(exc_info.value).lower()
    assert "1001" in str(exc_info.value)
    assert "1000" in str(exc_info.value)


def test_from_dict_accepts_text_at_max_length() -> None:
    """from_dict() should accept text == 1000 chars."""
    max_text = "e" * 1000
    data = {"id": 1, "text": max_text}

    todo = Todo.from_dict(data)
    assert todo.text == max_text
