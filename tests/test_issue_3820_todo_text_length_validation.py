"""Tests for issue #3820: Todo text length validation.

Feature: Add MAX_TEXT_LENGTH validation to prevent oversized todo text
that could cause JSON bloat, memory issues, or display problems.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo, MAX_TEXT_LENGTH


class TestTodoTextLengthValidation:
    """Tests for Todo text length limits."""

    def test_todo_text_exceeds_max_length_raises(self) -> None:
        """Todo constructor should reject text exceeding MAX_TEXT_LENGTH."""
        long_text = "a" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match="maximum.*length|exceeds|too long"):
            Todo(id=1, text=long_text)

    def test_todo_rename_exceeds_max_length_raises(self) -> None:
        """Todo.rename() should reject text exceeding MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="valid text")
        original_updated_at = todo.updated_at
        long_text = "b" * (MAX_TEXT_LENGTH + 1)

        with pytest.raises(ValueError, match="maximum.*length|exceeds|too long"):
            todo.rename(long_text)

        # Verify state unchanged after failed validation
        assert todo.text == "valid text"
        assert todo.updated_at == original_updated_at

    def test_todo_text_at_max_length_accepts(self) -> None:
        """Todo should accept text exactly at MAX_TEXT_LENGTH."""
        max_text = "c" * MAX_TEXT_LENGTH
        todo = Todo(id=1, text=max_text)
        assert todo.text == max_text

    def test_todo_rename_at_max_length_accepts(self) -> None:
        """Todo.rename() should accept text exactly at MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="valid text")
        max_text = "d" * MAX_TEXT_LENGTH
        todo.rename(max_text)
        assert todo.text == max_text

    def test_todo_rename_empty_still_rejected(self) -> None:
        """Empty rename should still be rejected (existing behavior)."""
        todo = Todo(id=1, text="valid text")
        with pytest.raises(ValueError, match="empty"):
            todo.rename("")

    def test_todo_from_dict_validates_text_length(self) -> None:
        """Todo.from_dict() should also validate text length."""
        long_text = "e" * (MAX_TEXT_LENGTH + 1)
        data = {"id": 1, "text": long_text}
        with pytest.raises(ValueError, match="maximum.*length|exceeds|too long"):
            Todo.from_dict(data)
