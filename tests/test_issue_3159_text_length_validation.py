"""Regression tests for Issue #3159: Add text length validation with configurable max length.

This test file ensures that todo text is validated against a maximum length
to prevent display issues, storage bloat, or denial of service.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo, MAX_TEXT_LENGTH


class TestTodoTextLengthValidation:
    """Tests for text length validation in Todo class."""

    def test_todo_rejects_text_exceeding_max_length(self) -> None:
        """Todo with text > MAX_TEXT_LENGTH chars raises ValueError in __post_init__."""
        long_text = "x" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError) as exc_info:
            Todo(id=1, text=long_text)
        # Error message should include actual length and max allowed
        error_msg = str(exc_info.value)
        assert str(MAX_TEXT_LENGTH + 1) in error_msg
        assert str(MAX_TEXT_LENGTH) in error_msg

    def test_todo_accepts_text_at_max_length(self) -> None:
        """Todo with text exactly at MAX_TEXT_LENGTH should be accepted."""
        text_at_max = "x" * MAX_TEXT_LENGTH
        todo = Todo(id=1, text=text_at_max)
        assert todo.text == text_at_max
        assert len(todo.text) == MAX_TEXT_LENGTH

    def test_todo_accepts_normal_text(self) -> None:
        """Todo with normal text should be accepted."""
        todo = Todo(id=1, text="Buy groceries")
        assert todo.text == "Buy groceries"

    def test_todo_rename_rejects_text_exceeding_max_length(self) -> None:
        """rename() with text > MAX_TEXT_LENGTH chars raises ValueError."""
        todo = Todo(id=1, text="Original text")
        long_text = "y" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError) as exc_info:
            todo.rename(long_text)
        # Error message should include actual length and max allowed
        error_msg = str(exc_info.value)
        assert str(MAX_TEXT_LENGTH + 1) in error_msg
        assert str(MAX_TEXT_LENGTH) in error_msg

    def test_todo_rename_accepts_text_at_max_length(self) -> None:
        """rename() with text exactly at MAX_TEXT_LENGTH should be accepted."""
        todo = Todo(id=1, text="Original text")
        text_at_max = "z" * MAX_TEXT_LENGTH
        todo.rename(text_at_max)
        assert todo.text == text_at_max

    def test_todo_rename_trims_whitespace_before_validation(self) -> None:
        """rename() should trim whitespace before validating length."""
        todo = Todo(id=1, text="Original text")
        # Text at max length + whitespace that would exceed after trim
        text_at_max = "a" * MAX_TEXT_LENGTH
        todo.rename(f"  {text_at_max}  ")
        assert todo.text == text_at_max
        assert len(todo.text) == MAX_TEXT_LENGTH

    def test_from_dict_rejects_text_exceeding_max_length(self) -> None:
        """from_dict() validates text length and raises clear error."""
        long_text = "b" * (MAX_TEXT_LENGTH + 1)
        data = {"id": 1, "text": long_text}
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict(data)
        # Error message should include actual length and max allowed
        error_msg = str(exc_info.value)
        assert str(MAX_TEXT_LENGTH + 1) in error_msg
        assert str(MAX_TEXT_LENGTH) in error_msg

    def test_from_dict_accepts_text_at_max_length(self) -> None:
        """from_dict() with text exactly at MAX_TEXT_LENGTH should be accepted."""
        text_at_max = "c" * MAX_TEXT_LENGTH
        data = {"id": 1, "text": text_at_max}
        todo = Todo.from_dict(data)
        assert todo.text == text_at_max

    def test_max_text_length_constant_value(self) -> None:
        """MAX_TEXT_LENGTH should be set to 1000 characters."""
        assert MAX_TEXT_LENGTH == 1000
