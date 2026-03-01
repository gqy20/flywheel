"""Tests for text field length validation (Issue #6481).

These tests verify that:
1. rename() method rejects text exceeding MAX_TEXT_LENGTH (1000 characters)
2. from_dict() method rejects text exceeding MAX_TEXT_LENGTH
3. Boundary case: exactly 1000 characters is accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


def test_rename_rejects_text_exceeding_max_length() -> None:
    """Todo.rename() should reject text longer than MAX_TEXT_LENGTH characters."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    # Create text that exceeds the limit
    long_text = "x" * (MAX_TEXT_LENGTH + 1)

    with pytest.raises(ValueError, match=r"text.*cannot exceed|text.*too long|length.*limit"):
        todo.rename(long_text)

    # Verify state unchanged after failed validation
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_rename_accepts_text_at_exact_max_length() -> None:
    """Todo.rename() should accept text that is exactly MAX_TEXT_LENGTH characters."""
    todo = Todo(id=1, text="original")

    # Create text at exactly the limit
    max_text = "x" * MAX_TEXT_LENGTH

    # Should not raise
    todo.rename(max_text)
    assert todo.text == max_text


def test_from_dict_rejects_text_exceeding_max_length() -> None:
    """Todo.from_dict() should reject text longer than MAX_TEXT_LENGTH characters."""
    long_text = "x" * (MAX_TEXT_LENGTH + 1)

    with pytest.raises(ValueError, match=r"text.*cannot exceed|text.*too long|length.*limit"):
        Todo.from_dict({"id": 1, "text": long_text})


def test_from_dict_accepts_text_at_exact_max_length() -> None:
    """Todo.from_dict() should accept text that is exactly MAX_TEXT_LENGTH characters."""
    max_text = "x" * MAX_TEXT_LENGTH

    todo = Todo.from_dict({"id": 1, "text": max_text})
    assert todo.text == max_text
