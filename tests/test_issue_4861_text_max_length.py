"""Tests for text max length validation (Issue #4861).

These tests verify that:
1. Todo.from_dict accepts text with length <= 10000 characters
2. Todo.from_dict rejects text with length > 10000 characters with clear error message
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_accepts_text_at_max_length() -> None:
    """Todo.from_dict should accept text with exactly 10000 characters."""
    todo = Todo.from_dict({"id": 1, "text": "a" * 10000})
    assert len(todo.text) == 10000


def test_todo_from_dict_rejects_text_exceeding_max_length() -> None:
    """Todo.from_dict should reject text longer than 10000 characters."""
    with pytest.raises(ValueError, match=r"maximum length|too long|exceeds"):
        Todo.from_dict({"id": 1, "text": "a" * 10001})
