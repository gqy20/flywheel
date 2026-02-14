"""Tests for Todo text length validation (Issue #3323).

These tests verify that:
1. Todo.rename() raises ValueError for text exceeding MAX_TEXT_LENGTH
2. Todo.from_dict() rejects 'text' field exceeding MAX_TEXT_LENGTH
3. Error message includes the character limit
4. Text of exactly MAX_TEXT_LENGTH (500 chars) succeeds
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


class TestTodoRenameTextLengthValidation:
    """Test rename() method text length validation."""

    def test_rename_exceeding_max_length_raises_valueerror(self) -> None:
        """rename() with text of 501 chars should raise ValueError."""
        todo = Todo(id=1, text="initial text")
        long_text = "a" * 501  # Exceeds MAX_TEXT_LENGTH of 500

        with pytest.raises(ValueError) as exc_info:
            todo.rename(long_text)

        error_message = str(exc_info.value)
        assert "500" in error_message, f"Error message should include limit: {error_message}"

    def test_rename_with_whitespace_exceeding_max_length_raises_valueerror(self) -> None:
        """rename() with text that becomes 501 chars after strip should raise ValueError."""
        todo = Todo(id=1, text="initial text")
        long_text = " " + "a" * 501 + " "  # 503 chars, becomes 501 after strip

        with pytest.raises(ValueError) as exc_info:
            todo.rename(long_text)

        error_message = str(exc_info.value)
        assert "500" in error_message, f"Error message should include limit: {error_message}"

    def test_rename_at_max_length_succeeds(self) -> None:
        """rename() with text of exactly 500 chars should succeed."""
        todo = Todo(id=1, text="initial text")
        max_length_text = "a" * 500  # Exactly MAX_TEXT_LENGTH

        todo.rename(max_length_text)
        assert todo.text == max_length_text

    def test_rename_below_max_length_succeeds(self) -> None:
        """rename() with text of 499 chars should succeed."""
        todo = Todo(id=1, text="initial text")
        valid_text = "a" * 499

        todo.rename(valid_text)
        assert todo.text == valid_text


class TestTodoFromDictTextLengthValidation:
    """Test from_dict() method text length validation."""

    def test_from_dict_exceeding_max_length_raises_valueerror(self) -> None:
        """from_dict() with text of 501 chars should raise ValueError."""
        long_text = "a" * 501
        data = {"id": 1, "text": long_text}

        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict(data)

        error_message = str(exc_info.value)
        assert "500" in error_message, f"Error message should include limit: {error_message}"
        assert "text" in error_message.lower(), f"Error message should mention 'text': {error_message}"

    def test_from_dict_at_max_length_succeeds(self) -> None:
        """from_dict() with text of exactly 500 chars should succeed."""
        max_length_text = "a" * 500
        data = {"id": 1, "text": max_length_text}

        todo = Todo.from_dict(data)
        assert todo.text == max_length_text

    def test_from_dict_below_max_length_succeeds(self) -> None:
        """from_dict() with text of 499 chars should succeed."""
        valid_text = "a" * 499
        data = {"id": 1, "text": valid_text}

        todo = Todo.from_dict(data)
        assert todo.text == valid_text


class TestMaxTextLengthConstant:
    """Test that MAX_TEXT_LENGTH constant exists and is correct."""

    def test_max_text_length_is_500(self) -> None:
        """MAX_TEXT_LENGTH should be 500 characters."""
        assert MAX_TEXT_LENGTH == 500
