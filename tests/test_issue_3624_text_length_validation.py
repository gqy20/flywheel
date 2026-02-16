"""Tests for Issue #3624 - Text length validation to prevent oversized input."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo

# Constants matching the implementation
MAX_TEXT_LENGTH = 10000


class TestTodoTextLengthValidation:
    """Test suite for text length validation in Todo class."""

    def test_todo_rename_rejects_text_exceeding_max_length(self) -> None:
        """Issue #3624: Todo.rename() should reject text exceeding 10000 chars."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        # Text exceeding max length should raise ValueError
        long_text = "x" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match=r"too long|exceeds|max"):
            todo.rename(long_text)

        # Verify state unchanged after failed validation
        assert todo.text == "original"
        assert todo.updated_at == original_updated_at

    def test_todo_rename_accepts_text_at_max_length(self) -> None:
        """Issue #3624: Todo.rename() should accept text at exactly 10000 chars."""
        todo = Todo(id=1, text="original")

        # Text at max length should be accepted
        max_text = "x" * MAX_TEXT_LENGTH
        todo.rename(max_text)
        assert todo.text == max_text

    def test_todo_rename_accepts_text_below_max_length(self) -> None:
        """Issue #3624: Todo.rename() should accept text below 10000 chars."""
        todo = Todo(id=1, text="original")

        # Text below max length should be accepted
        text_below_max = "x" * (MAX_TEXT_LENGTH - 1)
        todo.rename(text_below_max)
        assert todo.text == text_below_max

    def test_todo_constructor_rejects_text_exceeding_max_length(self) -> None:
        """Issue #3624: Todo constructor should reject text exceeding 10000 chars."""
        long_text = "y" * (MAX_TEXT_LENGTH + 1)

        with pytest.raises(ValueError, match=r"too long|exceeds|max"):
            Todo(id=1, text=long_text)

    def test_todo_constructor_accepts_text_at_max_length(self) -> None:
        """Issue #3624: Todo constructor should accept text at exactly 10000 chars."""
        max_text = "y" * MAX_TEXT_LENGTH
        todo = Todo(id=1, text=max_text)
        assert todo.text == max_text

    def test_todo_from_dict_rejects_text_exceeding_max_length(self) -> None:
        """Issue #3624: Todo.from_dict() should reject oversized text from JSON."""
        long_text = "z" * (MAX_TEXT_LENGTH + 1)
        data = {"id": 1, "text": long_text}

        with pytest.raises(ValueError, match=r"too long|exceeds|max"):
            Todo.from_dict(data)

    def test_todo_from_dict_accepts_text_at_max_length(self) -> None:
        """Issue #3624: Todo.from_dict() should accept text at exactly 10000 chars."""
        max_text = "z" * MAX_TEXT_LENGTH
        data = {"id": 1, "text": max_text}

        todo = Todo.from_dict(data)
        assert todo.text == max_text

    def test_error_message_includes_actual_and_max_length(self) -> None:
        """Issue #3624: Error message should include actual length and max length."""
        todo = Todo(id=1, text="original")
        long_text = "a" * 15000

        with pytest.raises(ValueError) as exc_info:
            todo.rename(long_text)

        error_msg = str(exc_info.value)
        # Should include actual length
        assert "15000" in error_msg
        # Should include max length
        assert str(MAX_TEXT_LENGTH) in error_msg
