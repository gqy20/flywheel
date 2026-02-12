"""Tests for text field length limit (Issue #2940).

Security: Todo text field has no length limit, allowing storage of extremely
large strings (10MB+ per todo) as potential DoS vector.

These tests verify that:
1. Todo.from_dict rejects text longer than MAX_TEXT_LENGTH (1MB)
2. Error message clearly indicates the limit
3. Normal-length text still works
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo

# 1MB is the maximum allowed text length
_MAX_TEXT_LENGTH = 1024 * 1024  # 1MB


def test_todo_from_dict_rejects_oversized_text() -> None:
    """Todo.from_dict should reject text longer than 1MB."""
    # Create a text field that exceeds the limit by 1 byte
    oversized_text = "x" * (_MAX_TEXT_LENGTH + 1)

    with pytest.raises(ValueError, match=r"text.*too long|maximum|limit|1MB|1048576"):
        Todo.from_dict({"id": 1, "text": oversized_text})


def test_todo_from_dict_accepts_text_at_limit() -> None:
    """Todo.from_dict should accept text exactly at the 1MB limit."""
    # Create a text field exactly at the limit
    max_length_text = "a" * _MAX_TEXT_LENGTH

    todo = Todo.from_dict({"id": 1, "text": max_length_text})
    assert len(todo.text) == _MAX_TEXT_LENGTH
    assert todo.text == max_length_text


def test_todo_from_dict_accepts_normal_text() -> None:
    """Todo.from_dict should still work with normal-length text."""
    # Normal text should work fine
    todo = Todo.from_dict({"id": 1, "text": "Buy groceries"})
    assert todo.text == "Buy groceries"


def test_todo_from_dict_rejects_oversized_text_clear_error_message() -> None:
    """Error message should clearly indicate the size limit."""
    oversized_text = "y" * (_MAX_TEXT_LENGTH + 100)

    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": 1, "text": oversized_text})

    error_message = str(exc_info.value).lower()
    # Check that error message contains helpful information
    assert "text" in error_message
    assert ("too long" in error_message or "limit" in error_message or "maximum" in error_message)
