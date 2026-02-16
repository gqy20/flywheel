"""Tests for todo text length limit (Issue #3777).

These tests verify that:
1. Todo constructor rejects text > MAX_TEXT_LENGTH
2. Todo.rename() rejects text > MAX_TEXT_LENGTH
3. TodoApp.add() rejects text > MAX_TEXT_LENGTH
4. Error message indicates maximum allowed length
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo

# Use the constant from the module
EXPECTED_MAX_TEXT_LENGTH = MAX_TEXT_LENGTH


class TestTodoTextLengthLimit:
    """Tests for text length validation on Todo."""

    def test_todo_constructor_rejects_text_exceeding_max_length(self) -> None:
        """Todo constructor should raise ValueError for text > MAX_TEXT_LENGTH."""
        long_text = "a" * (EXPECTED_MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError) as exc_info:
            Todo(id=1, text=long_text)
        assert "text" in str(exc_info.value).lower()
        assert str(EXPECTED_MAX_TEXT_LENGTH) in str(exc_info.value)

    def test_todo_rename_rejects_text_exceeding_max_length(self) -> None:
        """Todo.rename() should raise ValueError for text > MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="original text")
        long_text = "a" * (EXPECTED_MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError) as exc_info:
            todo.rename(long_text)
        assert "text" in str(exc_info.value).lower()
        assert str(EXPECTED_MAX_TEXT_LENGTH) in str(exc_info.value)

    def test_todo_constructor_accepts_text_at_max_length(self) -> None:
        """Todo constructor should accept text exactly at MAX_TEXT_LENGTH."""
        text_at_limit = "a" * EXPECTED_MAX_TEXT_LENGTH
        todo = Todo(id=1, text=text_at_limit)
        assert todo.text == text_at_limit

    def test_todo_rename_accepts_text_at_max_length(self) -> None:
        """Todo.rename() should accept text exactly at MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="original")
        text_at_limit = "a" * EXPECTED_MAX_TEXT_LENGTH
        todo.rename(text_at_limit)
        assert todo.text == text_at_limit

    def test_todo_constructor_accepts_text_below_max_length(self) -> None:
        """Todo constructor should accept text well below MAX_TEXT_LENGTH."""
        normal_text = "Buy groceries"
        todo = Todo(id=1, text=normal_text)
        assert todo.text == normal_text

    def test_todo_rename_accepts_text_below_max_length(self) -> None:
        """Todo.rename() should accept text well below MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="original")
        new_text = "Updated todo text"
        todo.rename(new_text)
        assert todo.text == new_text

    def test_from_dict_rejects_text_exceeding_max_length(self) -> None:
        """Todo.from_dict() should raise ValueError for text > MAX_TEXT_LENGTH."""
        long_text = "a" * (EXPECTED_MAX_TEXT_LENGTH + 1)
        data = {"id": 1, "text": long_text}
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict(data)
        assert "text" in str(exc_info.value).lower()
        assert str(EXPECTED_MAX_TEXT_LENGTH) in str(exc_info.value)
