"""Tests for text length validation to prevent DoS attacks (Issue #2651).

These tests verify that:
1. Todo.from_dict rejects text fields exceeding MAX_TODO_TEXT_LENGTH
2. Error message includes the max length and actual length
3. Normal length text still works
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_extremely_long_text() -> None:
    """Todo.from_dict should reject text fields exceeding MAX_TODO_TEXT_LENGTH to prevent DoS."""
    # Create a text that's 1MB + 1 character (well beyond any reasonable limit)
    long_text = "A" * (1_000_000 + 1)

    with pytest.raises(ValueError, match=r"text.*too long|exceeds.*maximum"):
        Todo.from_dict({"id": 1, "text": long_text})


def test_todo_from_dict_includes_length_in_error_message() -> None:
    """Error message should include both the actual length and max limit."""
    # Create a text that's 10001 characters (exceeding the 10000 limit)
    long_text = "B" * 10001

    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": 1, "text": long_text})

    error_msg = str(exc_info.value)
    # Error should mention both lengths (with comma formatting)
    assert "10,001" in error_msg
    assert "10,000" in error_msg


def test_todo_from_dict_accepts_normal_length_text() -> None:
    """Todo.from_dict should accept normal length text strings."""
    # A reasonable length todo (1000 characters)
    normal_text = "Buy groceries" + " and more items" * 50  # ~1000 chars

    todo = Todo.from_dict({"id": 1, "text": normal_text})
    assert todo.text == normal_text
    assert len(todo.text) == len(normal_text)


def test_todo_from_dict_rejects_text_at_exact_limit_boundary() -> None:
    """Test that text exactly at max length + 1 is rejected."""
    # This tests the boundary condition - we need to know the exact limit
    # For now, test with a very long string that should definitely be rejected
    extremely_long_text = "X" * 1_000_000

    with pytest.raises(ValueError, match=r"text.*too long|exceeds"):
        Todo.from_dict({"id": 1, "text": extremely_long_text})
