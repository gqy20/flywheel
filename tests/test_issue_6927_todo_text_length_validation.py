"""Tests for Todo text maximum length validation (Issue #6927).

These tests verify that:
1. Todo text longer than 10,000 characters is rejected
2. Todo text at exactly 10,000 characters is accepted (boundary)
3. Validation occurs in __post_init__, rename(), and from_dict()
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo

# Maximum allowed text length as specified in the issue
MAX_TEXT_LENGTH = 10000


def test_todo_creation_rejects_oversized_text() -> None:
    """Creating a Todo with text > 10,000 chars should raise ValueError."""
    oversized_text = "x" * (MAX_TEXT_LENGTH + 1)

    with pytest.raises(ValueError, match=r"text.*too long|length|10.?000|maximum"):
        Todo(id=1, text=oversized_text)


def test_todo_rename_rejects_oversized_text() -> None:
    """rename() should reject text > 10,000 chars."""
    todo = Todo(id=1, text="valid text")
    oversized_text = "y" * (MAX_TEXT_LENGTH + 1)

    with pytest.raises(ValueError, match=r"text.*too long|length|10.?000|maximum"):
        todo.rename(oversized_text)


def test_todo_from_dict_rejects_oversized_text() -> None:
    """from_dict() should reject text > 10,000 chars."""
    oversized_text = "z" * (MAX_TEXT_LENGTH + 1)
    data = {"id": 1, "text": oversized_text}

    with pytest.raises(ValueError, match=r"text.*too long|length|10.?000|maximum"):
        Todo.from_dict(data)


def test_todo_creation_accepts_max_length_text() -> None:
    """Creating a Todo with exactly 10,000 chars should work (boundary)."""
    max_length_text = "a" * MAX_TEXT_LENGTH

    todo = Todo(id=1, text=max_length_text)

    assert len(todo.text) == MAX_TEXT_LENGTH
    assert todo.text == max_length_text


def test_todo_rename_accepts_max_length_text() -> None:
    """rename() should accept exactly 10,000 chars (boundary)."""
    todo = Todo(id=1, text="original")
    max_length_text = "b" * MAX_TEXT_LENGTH

    todo.rename(max_length_text)

    assert len(todo.text) == MAX_TEXT_LENGTH
    assert todo.text == max_length_text


def test_todo_from_dict_accepts_max_length_text() -> None:
    """from_dict() should accept exactly 10,000 chars (boundary)."""
    max_length_text = "c" * MAX_TEXT_LENGTH
    data = {"id": 1, "text": max_length_text}

    todo = Todo.from_dict(data)

    assert len(todo.text) == MAX_TEXT_LENGTH
    assert todo.text == max_length_text
