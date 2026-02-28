"""Tests for Todo text maximum length validation (Issue #6340).

These tests verify that:
1. Todo text has a maximum length limit (1000 characters)
2. Creating a Todo with text exceeding the limit raises ValueError
3. Renaming a Todo with text exceeding the limit raises ValueError
4. Boundary values (exactly at max length) work correctly
5. Error message clearly indicates the maximum allowed length
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo

# Maximum allowed text length as specified in the issue
MAX_TEXT_LENGTH = 1000


class TestTodoTextMaxLengthCreation:
    """Tests for Todo creation with text length validation."""

    def test_create_todo_with_text_exceeding_max_length_raises_error(self) -> None:
        """Todo(text='a'*10001) should raise ValueError."""
        long_text = "a" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError) as exc_info:
            Todo(id=1, text=long_text)
        error_message = str(exc_info.value)
        assert "text" in error_message.lower()
        assert str(MAX_TEXT_LENGTH) in error_message

    def test_create_todo_with_text_at_max_length_succeeds(self) -> None:
        """Todo(text='a'*1000) should be created successfully."""
        max_length_text = "a" * MAX_TEXT_LENGTH
        todo = Todo(id=1, text=max_length_text)
        assert todo.text == max_length_text
        assert len(todo.text) == MAX_TEXT_LENGTH

    def test_create_todo_with_text_below_max_length_succeeds(self) -> None:
        """Todo with text shorter than max length should work."""
        short_text = "a" * 500
        todo = Todo(id=1, text=short_text)
        assert todo.text == short_text


class TestTodoTextMaxLengthRename:
    """Tests for Todo.rename() with text length validation."""

    def test_rename_to_text_exceeding_max_length_raises_error(self) -> None:
        """todo.rename('a'*10001) should raise ValueError."""
        todo = Todo(id=1, text="initial text")
        long_text = "a" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError) as exc_info:
            todo.rename(long_text)
        error_message = str(exc_info.value)
        assert "text" in error_message.lower()
        assert str(MAX_TEXT_LENGTH) in error_message

    def test_rename_to_text_at_max_length_succeeds(self) -> None:
        """todo.rename() with text at max length should succeed."""
        todo = Todo(id=1, text="initial text")
        max_length_text = "b" * MAX_TEXT_LENGTH
        todo.rename(max_length_text)
        assert todo.text == max_length_text

    def test_rename_to_text_below_max_length_succeeds(self) -> None:
        """todo.rename() with text shorter than max length should work."""
        todo = Todo(id=1, text="initial text")
        short_text = "renamed"
        todo.rename(short_text)
        assert todo.text == short_text


class TestTodoTextMaxLengthEdgeCases:
    """Edge case tests for text length validation."""

    def test_create_todo_with_single_character_succeeds(self) -> None:
        """Todo with minimal valid text should work."""
        todo = Todo(id=1, text="x")
        assert todo.text == "x"

    def test_rename_to_single_character_succeeds(self) -> None:
        """Renaming to single character should work."""
        todo = Todo(id=1, text="initial text")
        todo.rename("y")
        assert todo.text == "y"

    def test_create_todo_with_unicode_text_respects_length(self) -> None:
        """Unicode characters should be counted correctly for length."""
        # Each emoji is typically 1-4 bytes in UTF-8 but counts as 1 character in Python
        unicode_text = "😀" * MAX_TEXT_LENGTH
        todo = Todo(id=1, text=unicode_text)
        assert len(todo.text) == MAX_TEXT_LENGTH

    def test_create_todo_with_unicode_exceeding_max_raises_error(self) -> None:
        """Unicode text exceeding max length should raise ValueError."""
        unicode_text = "😀" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError) as exc_info:
            Todo(id=1, text=unicode_text)
        error_message = str(exc_info.value)
        assert "text" in error_message.lower()
        assert str(MAX_TEXT_LENGTH) in error_message
