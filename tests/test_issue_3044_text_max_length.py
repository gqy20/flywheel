"""Tests for Todo text maximum length validation (Issue #3044).

These tests verify that:
1. rename() method rejects text exceeding MAX_TEXT_LENGTH
2. from_dict() rejects text exceeding MAX_TEXT_LENGTH
3. rename() accepts text at exactly MAX_TEXT_LENGTH boundary
4. from_dict() accepts text at exactly MAX_TEXT_LENGTH boundary
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


class TestRenameTextMaxLength:
    """Tests for rename() method max length validation."""

    def test_rename_accepts_exact_max_length_text(self) -> None:
        """rename() should accept text that is exactly MAX_TEXT_LENGTH characters."""
        todo = Todo(id=1, text="original")
        max_length_text = "a" * MAX_TEXT_LENGTH
        todo.rename(max_length_text)
        assert todo.text == max_length_text

    def test_rename_accepts_shorter_than_max_length_text(self) -> None:
        """rename() should accept text shorter than MAX_TEXT_LENGTH characters."""
        todo = Todo(id=1, text="original")
        shorter_text = "a" * (MAX_TEXT_LENGTH - 1)
        todo.rename(shorter_text)
        assert todo.text == shorter_text

    def test_rename_rejects_text_exceeding_max_length(self) -> None:
        """rename() should raise ValueError when text exceeds MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="original")
        too_long_text = "a" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match=r"exceeds maximum|too long|text.*length"):
            todo.rename(too_long_text)

    def test_rename_error_message_includes_max_length(self) -> None:
        """rename() error message should include the maximum allowed length."""
        todo = Todo(id=1, text="original")
        too_long_text = "a" * (MAX_TEXT_LENGTH + 100)
        with pytest.raises(ValueError, match=str(MAX_TEXT_LENGTH)):
            todo.rename(too_long_text)


class TestFromDictTextMaxLength:
    """Tests for from_dict() method max length validation."""

    def test_from_dict_accepts_exact_max_length_text(self) -> None:
        """from_dict() should accept text that is exactly MAX_TEXT_LENGTH characters."""
        max_length_text = "b" * MAX_TEXT_LENGTH
        todo = Todo.from_dict({"id": 1, "text": max_length_text})
        assert todo.text == max_length_text

    def test_from_dict_accepts_shorter_than_max_length_text(self) -> None:
        """from_dict() should accept text shorter than MAX_TEXT_LENGTH characters."""
        shorter_text = "b" * (MAX_TEXT_LENGTH - 1)
        todo = Todo.from_dict({"id": 1, "text": shorter_text})
        assert todo.text == shorter_text

    def test_from_dict_rejects_text_exceeding_max_length(self) -> None:
        """from_dict() should raise ValueError when text exceeds MAX_TEXT_LENGTH."""
        too_long_text = "b" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match=r"exceeds maximum|too long|text.*length"):
            Todo.from_dict({"id": 1, "text": too_long_text})

    def test_from_dict_error_message_includes_max_length(self) -> None:
        """from_dict() error message should include the maximum allowed length."""
        too_long_text = "b" * (MAX_TEXT_LENGTH + 100)
        with pytest.raises(ValueError, match=str(MAX_TEXT_LENGTH)):
            Todo.from_dict({"id": 1, "text": too_long_text})
