"""Tests for text length validation (Issue #4861).

These tests verify that:
1. Todo.from_dict accepts text up to 10000 characters
2. Todo.from_dict rejects text longer than 10000 characters with clear error
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo

MAX_TEXT_LENGTH = 10000


def test_todo_from_dict_accepts_max_length_text() -> None:
    """Todo.from_dict should accept text that is exactly 10000 characters."""
    todo = Todo.from_dict({"id": 1, "text": "a" * MAX_TEXT_LENGTH})
    assert len(todo.text) == MAX_TEXT_LENGTH


def test_todo_from_dict_rejects_over_max_length_text() -> None:
    """Todo.from_dict should reject text longer than 10000 characters."""
    with pytest.raises(ValueError, match=r"text.*length|text.*max|text.*10000"):
        Todo.from_dict({"id": 1, "text": "a" * (MAX_TEXT_LENGTH + 1)})
