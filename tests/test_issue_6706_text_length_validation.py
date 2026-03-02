"""Tests for Todo text length validation (Issue #6706).

These tests verify that:
1. Todo text has a maximum length limit (1000 chars by default)
2. Creating a Todo with text > MAX_TEXT_LENGTH raises ValueError
3. rename() with text > MAX_TEXT_LENGTH raises ValueError
4. from_dict() with text > MAX_TEXT_LENGTH raises ValueError
5. Error messages clearly state the limit and actual length
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


class TestTextLengthValidation:
    """Test suite for Todo text length validation."""

    def test_max_text_length_constant_exists(self) -> None:
        """MAX_TEXT_LENGTH constant should be defined and default to 1000."""
        assert MAX_TEXT_LENGTH is not None
        assert MAX_TEXT_LENGTH == 1000

    def test_todo_accepts_text_at_max_length(self) -> None:
        """Todo should accept text that is exactly at MAX_TEXT_LENGTH."""
        text_at_limit = "a" * MAX_TEXT_LENGTH
        todo = Todo(id=1, text=text_at_limit)
        assert len(todo.text) == MAX_TEXT_LENGTH

    def test_todo_rejects_text_exceeding_max_length(self) -> None:
        """Todo should reject text that exceeds MAX_TEXT_LENGTH."""
        text_over_limit = "a" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError) as exc_info:
            Todo(id=1, text=text_over_limit)

        error_msg = str(exc_info.value)
        assert "text" in error_msg.lower()
        assert str(MAX_TEXT_LENGTH) in error_msg
        assert str(len(text_over_limit)) in error_msg

    def test_rename_accepts_text_at_max_length(self) -> None:
        """rename() should accept text that is exactly at MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="original")
        text_at_limit = "b" * MAX_TEXT_LENGTH
        todo.rename(text_at_limit)
        assert todo.text == text_at_limit

    def test_rename_rejects_text_exceeding_max_length(self) -> None:
        """rename() should reject text that exceeds MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="original")
        text_over_limit = "c" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError) as exc_info:
            todo.rename(text_over_limit)

        error_msg = str(exc_info.value)
        assert "text" in error_msg.lower()
        assert str(MAX_TEXT_LENGTH) in error_msg

    def test_from_dict_accepts_text_at_max_length(self) -> None:
        """from_dict() should accept text that is exactly at MAX_TEXT_LENGTH."""
        text_at_limit = "d" * MAX_TEXT_LENGTH
        todo = Todo.from_dict({"id": 1, "text": text_at_limit})
        assert len(todo.text) == MAX_TEXT_LENGTH

    def test_from_dict_rejects_text_exceeding_max_length(self) -> None:
        """from_dict() should reject text that exceeds MAX_TEXT_LENGTH."""
        text_over_limit = "e" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": 1, "text": text_over_limit})

        error_msg = str(exc_info.value)
        assert "text" in error_msg.lower()
        assert str(MAX_TEXT_LENGTH) in error_msg

    def test_empty_text_not_validated_in_constructor(self) -> None:
        """Empty text is not validated in constructor (only in rename).

        The constructor allows empty text for flexibility. Only rename()
        enforces the 'cannot be empty' rule. Length validation is still
        enforced in constructor.
        """
        # Constructor should allow empty text (existing behavior)
        todo = Todo(id=1, text="")
        assert todo.text == ""

    def test_rename_empty_text_validation_takes_precedence(self) -> None:
        """rename() with empty text should raise 'cannot be empty' error."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError) as exc_info:
            todo.rename("")
        error_msg = str(exc_info.value)
        assert "empty" in error_msg.lower()

    def test_whitespace_only_text_is_stripped_and_validated(self) -> None:
        """Whitespace-only text should be stripped and trigger empty validation."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError) as exc_info:
            todo.rename("   ")
        error_msg = str(exc_info.value)
        assert "empty" in error_msg.lower()

    def test_long_text_with_leading_trailing_whitespace(self) -> None:
        """Long text with whitespace that exceeds limit after stripping should be rejected."""
        todo = Todo(id=1, text="original")
        # Create text that's at the limit but with spaces that push it over after strip consideration
        text_with_spaces = "  " + "f" * MAX_TEXT_LENGTH + "  "
        # After strip, this should still be MAX_TEXT_LENGTH and valid
        todo.rename(text_with_spaces)
        assert len(todo.text) == MAX_TEXT_LENGTH
