"""Tests for text length limit validation (Issue #6745).

These tests verify that:
1. Todo.from_dict accepts text up to MAX_TEXT_LENGTH characters
2. Todo.from_dict raises ValueError for text exceeding MAX_TEXT_LENGTH
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo, MAX_TEXT_LENGTH


def test_todo_from_dict_accepts_text_at_max_length() -> None:
    """Todo.from_dict should accept text with exactly MAX_TEXT_LENGTH characters."""
    text_at_limit = "x" * MAX_TEXT_LENGTH
    todo = Todo.from_dict({"id": 1, "text": text_at_limit})
    assert todo.text == text_at_limit
    assert len(todo.text) == MAX_TEXT_LENGTH


def test_todo_from_dict_rejects_text_exceeding_max_length() -> None:
    """Todo.from_dict should reject text exceeding MAX_TEXT_LENGTH characters."""
    text_over_limit = "x" * (MAX_TEXT_LENGTH + 1)
    with pytest.raises(ValueError, match=r"text.*too long|exceeds.*limit|maximum"):
        Todo.from_dict({"id": 1, "text": text_over_limit})


def test_todo_from_dict_rejects_extremely_long_text() -> None:
    """Todo.from_dict should reject extremely long text (e.g., 1MB string)."""
    extremely_long_text = "x" * (1024 * 1024)  # 1MB
    with pytest.raises(ValueError, match=r"text.*too long|exceeds.*limit|maximum"):
        Todo.from_dict({"id": 1, "text": extremely_long_text})


def test_max_text_length_is_10000() -> None:
    """MAX_TEXT_LENGTH should be 10000 characters as per issue requirement."""
    assert MAX_TEXT_LENGTH == 10000
