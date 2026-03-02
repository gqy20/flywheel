"""Tests for Todo text length validation (Issue #6706).

These tests verify that:
1. Todo with text > MAX_TEXT_LENGTH raises ValueError in constructor
2. Todo with text > MAX_TEXT_LENGTH raises ValueError in rename()
3. Todo with text > MAX_TEXT_LENGTH raises ValueError in from_dict()
4. Default MAX_TEXT_LENGTH is 1000 characters
5. Error message clearly states the limit and actual length
6. Text at exactly MAX_TEXT_LENGTH is accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


class TestTextLengthValidation:
    """Test text length validation for Todo items."""

    def test_max_text_length_is_1000(self) -> None:
        """MAX_TEXT_LENGTH constant should be 1000 characters."""
        assert MAX_TEXT_LENGTH == 1000

    def test_text_exactly_at_max_length_accepted_in_constructor(self) -> None:
        """Todo with text at exactly MAX_TEXT_LENGTH should be accepted."""
        text_at_limit = "a" * MAX_TEXT_LENGTH
        todo = Todo(id=1, text=text_at_limit)
        assert len(todo.text) == MAX_TEXT_LENGTH

    def test_text_exceeding_max_length_raises_in_constructor(self) -> None:
        """Todo with text > MAX_TEXT_LENGTH should raise ValueError in constructor."""
        text_over_limit = "a" * (MAX_TEXT_LENGTH + 1)

        with pytest.raises(ValueError) as exc_info:
            Todo(id=1, text=text_over_limit)

        # Error message should state limit and actual length
        error_msg = str(exc_info.value)
        assert "1000" in error_msg
        assert "1001" in error_msg

    def test_text_exceeding_max_length_raises_in_rename(self) -> None:
        """rename() with text > MAX_TEXT_LENGTH should raise ValueError."""
        todo = Todo(id=1, text="valid text")
        text_over_limit = "b" * (MAX_TEXT_LENGTH + 1)

        with pytest.raises(ValueError) as exc_info:
            todo.rename(text_over_limit)

        error_msg = str(exc_info.value)
        assert "1000" in error_msg
        assert "1001" in error_msg

    def test_text_exactly_at_max_length_accepted_in_rename(self) -> None:
        """rename() with text at exactly MAX_TEXT_LENGTH should be accepted."""
        todo = Todo(id=1, text="valid text")
        text_at_limit = "c" * MAX_TEXT_LENGTH
        todo.rename(text_at_limit)
        assert len(todo.text) == MAX_TEXT_LENGTH

    def test_text_exceeding_max_length_raises_in_from_dict(self) -> None:
        """from_dict() with text > MAX_TEXT_LENGTH should raise ValueError."""
        text_over_limit = "d" * (MAX_TEXT_LENGTH + 1)
        data = {
            "id": 1,
            "text": text_over_limit,
            "done": False,
        }

        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict(data)

        error_msg = str(exc_info.value)
        assert "1000" in error_msg
        assert "1001" in error_msg

    def test_text_exactly_at_max_length_accepted_in_from_dict(self) -> None:
        """from_dict() with text at exactly MAX_TEXT_LENGTH should be accepted."""
        text_at_limit = "e" * MAX_TEXT_LENGTH
        data = {
            "id": 1,
            "text": text_at_limit,
            "done": False,
        }
        todo = Todo.from_dict(data)
        assert len(todo.text) == MAX_TEXT_LENGTH

    def test_whitespace_text_still_validates_empty(self) -> None:
        """Whitespace-only text should still raise empty string error, not length error."""
        todo = Todo(id=1, text="valid text")

        with pytest.raises(ValueError) as exc_info:
            todo.rename("   ")  # whitespace only

        # Should be empty error, not length error
        assert "empty" in str(exc_info.value).lower()

    def test_error_message_includes_actual_length(self) -> None:
        """Error message should include actual text length for debugging."""
        text_over_limit = "x" * 1500
        data = {
            "id": 1,
            "text": text_over_limit,
        }

        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict(data)

        error_msg = str(exc_info.value)
        # Should mention the actual length
        assert "1500" in error_msg
