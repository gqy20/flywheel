"""Tests for todo text max length validation (Issue #4259).

These tests verify that:
1. Todo.rename() rejects text longer than MAX_TEXT_LENGTH
2. Todo.from_dict() rejects data['text'] longer than MAX_TEXT_LENGTH
3. Error message clearly states the limit
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


class TestRenameMaxLength:
    """Tests for Todo.rename() max length validation."""

    def test_rename_with_text_at_max_length_succeeds(self) -> None:
        """rename() with text at exactly MAX_TEXT_LENGTH should succeed."""
        todo = Todo(id=1, text="initial")
        max_length_text = "a" * MAX_TEXT_LENGTH

        # Should not raise
        todo.rename(max_length_text)
        assert todo.text == max_length_text

    def test_rename_with_text_exceeding_max_length_raises(self) -> None:
        """rename() with text exceeding MAX_TEXT_LENGTH should raise ValueError."""
        todo = Todo(id=1, text="initial")
        too_long_text = "a" * (MAX_TEXT_LENGTH + 1)

        with pytest.raises(ValueError, match=r"cannot exceed|too long|max.*length"):
            todo.rename(too_long_text)

    def test_rename_error_message_states_limit(self) -> None:
        """rename() error message should clearly state the max length limit."""
        todo = Todo(id=1, text="initial")
        too_long_text = "b" * (MAX_TEXT_LENGTH + 100)

        with pytest.raises(ValueError) as exc_info:
            todo.rename(too_long_text)

        # Error message should contain the limit value
        error_message = str(exc_info.value)
        assert str(MAX_TEXT_LENGTH) in error_message


class TestFromDictMaxLength:
    """Tests for Todo.from_dict() max length validation."""

    def test_from_dict_with_text_at_max_length_succeeds(self) -> None:
        """from_dict() with text at exactly MAX_TEXT_LENGTH should succeed."""
        max_length_text = "x" * MAX_TEXT_LENGTH
        data = {"id": 1, "text": max_length_text}

        todo = Todo.from_dict(data)
        assert todo.text == max_length_text

    def test_from_dict_with_text_exceeding_max_length_raises(self) -> None:
        """from_dict() with text exceeding MAX_TEXT_LENGTH should raise ValueError."""
        too_long_text = "y" * (MAX_TEXT_LENGTH + 1)
        data = {"id": 1, "text": too_long_text}

        with pytest.raises(ValueError, match=r"cannot exceed|too long|max.*length"):
            Todo.from_dict(data)

    def test_from_dict_error_message_states_limit(self) -> None:
        """from_dict() error message should clearly state the max length limit."""
        too_long_text = "z" * (MAX_TEXT_LENGTH + 500)
        data = {"id": 1, "text": too_long_text}

        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict(data)

        # Error message should contain the limit value
        error_message = str(exc_info.value)
        assert str(MAX_TEXT_LENGTH) in error_message


class TestMaxTextLengthConstant:
    """Tests for MAX_TEXT_LENGTH constant."""

    def test_max_text_length_is_defined(self) -> None:
        """MAX_TEXT_LENGTH should be defined as a module-level constant."""
        assert MAX_TEXT_LENGTH is not None
        assert isinstance(MAX_TEXT_LENGTH, int)

    def test_max_text_length_is_reasonable(self) -> None:
        """MAX_TEXT_LENGTH should be a reasonable value (e.g., 10000)."""
        # Should be at least 1000 to allow normal todos
        assert MAX_TEXT_LENGTH >= 1000
        # Should not be unreasonably large (to prevent storage bloat)
        assert MAX_TEXT_LENGTH <= 100000
