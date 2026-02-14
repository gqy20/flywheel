"""Tests for text length validation in Todo.rename() and from_dict().

Issue #3323: Add text length validation to prevent storage bloat and UI issues.
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


class TestTodoRenameTextLengthValidation:
    """Tests for text length validation in Todo.rename()."""

    def test_rename_rejects_text_exceeding_max_length(self) -> None:
        """rename() should raise ValueError for text exceeding MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        # Create text that exceeds MAX_TEXT_LENGTH (501 chars when limit is 500)
        long_text = "a" * (MAX_TEXT_LENGTH + 1)

        with pytest.raises(ValueError, match=r"Todo text cannot exceed \d+ characters"):
            todo.rename(long_text)

        # Verify state unchanged after failed validation
        assert todo.text == "original"
        assert todo.updated_at == original_updated_at

    def test_rename_accepts_text_at_max_length(self) -> None:
        """rename() should accept text exactly at MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="original")

        # Create text exactly at MAX_TEXT_LENGTH (500 chars)
        max_text = "b" * MAX_TEXT_LENGTH
        todo.rename(max_text)

        assert todo.text == max_text
        assert len(todo.text) == MAX_TEXT_LENGTH

    def test_rename_accepts_text_below_max_length(self) -> None:
        """rename() should accept text below MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="original")

        # Create text below MAX_TEXT_LENGTH
        short_text = "short text"
        todo.rename(short_text)

        assert todo.text == short_text


class TestTodoFromDictTextLengthValidation:
    """Tests for text length validation in Todo.from_dict()."""

    def test_from_dict_rejects_text_exceeding_max_length(self) -> None:
        """from_dict() should raise ValueError for text exceeding MAX_TEXT_LENGTH."""
        # Create text that exceeds MAX_TEXT_LENGTH (501 chars when limit is 500)
        long_text = "x" * (MAX_TEXT_LENGTH + 1)
        data = {"id": 1, "text": long_text}

        with pytest.raises(ValueError, match=r"Todo text cannot exceed \d+ characters"):
            Todo.from_dict(data)

    def test_from_dict_accepts_text_at_max_length(self) -> None:
        """from_dict() should accept text exactly at MAX_TEXT_LENGTH."""
        # Create text exactly at MAX_TEXT_LENGTH (500 chars)
        max_text = "y" * MAX_TEXT_LENGTH
        data = {"id": 1, "text": max_text}

        todo = Todo.from_dict(data)
        assert todo.text == max_text
        assert len(todo.text) == MAX_TEXT_LENGTH

    def test_from_dict_accepts_text_below_max_length(self) -> None:
        """from_dict() should accept text below MAX_TEXT_LENGTH."""
        data = {"id": 1, "text": "short text"}

        todo = Todo.from_dict(data)
        assert todo.text == "short text"
