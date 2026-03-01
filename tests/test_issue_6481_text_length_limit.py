"""Tests for text field length limit validation (Issue #6481).

These tests verify that:
1. rename() method rejects text exceeding 1000 characters
2. from_dict() method rejects text exceeding 1000 characters
3. Boundary case: exactly 1000 characters is accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


class TestRenameTextLengthValidation:
    """Tests for rename() method text length validation."""

    def test_rename_rejects_text_exceeding_max_length(self) -> None:
        """rename() should reject text exceeding MAX_TEXT_LENGTH characters."""
        todo = Todo(id=1, text="original task")
        long_text = "a" * (MAX_TEXT_LENGTH + 1)

        with pytest.raises(ValueError, match=r"exceeds.*limit|maximum.*length"):
            todo.rename(long_text)

    def test_rename_accepts_text_at_max_length(self) -> None:
        """rename() should accept text with exactly MAX_TEXT_LENGTH characters."""
        todo = Todo(id=1, text="original task")
        max_length_text = "a" * MAX_TEXT_LENGTH

        # Should not raise
        todo.rename(max_length_text)
        assert todo.text == max_length_text

    def test_rename_accepts_text_below_max_length(self) -> None:
        """rename() should accept text shorter than MAX_TEXT_LENGTH characters."""
        todo = Todo(id=1, text="original task")
        short_text = "a" * (MAX_TEXT_LENGTH - 1)

        # Should not raise
        todo.rename(short_text)
        assert todo.text == short_text


class TestFromDictTextLengthValidation:
    """Tests for from_dict() method text length validation."""

    def test_from_dict_rejects_text_exceeding_max_length(self) -> None:
        """from_dict() should reject text exceeding MAX_TEXT_LENGTH characters."""
        long_text = "a" * (MAX_TEXT_LENGTH + 1)
        data = {"id": 1, "text": long_text}

        with pytest.raises(ValueError, match=r"exceeds.*maximum.*length"):
            Todo.from_dict(data)

    def test_from_dict_accepts_text_at_max_length(self) -> None:
        """from_dict() should accept text with exactly MAX_TEXT_LENGTH characters."""
        max_length_text = "a" * MAX_TEXT_LENGTH
        data = {"id": 1, "text": max_length_text}

        # Should not raise
        todo = Todo.from_dict(data)
        assert todo.text == max_length_text

    def test_from_dict_accepts_text_below_max_length(self) -> None:
        """from_dict() should accept text shorter than MAX_TEXT_LENGTH characters."""
        short_text = "a" * (MAX_TEXT_LENGTH - 1)
        data = {"id": 1, "text": short_text}

        # Should not raise
        todo = Todo.from_dict(data)
        assert todo.text == short_text
