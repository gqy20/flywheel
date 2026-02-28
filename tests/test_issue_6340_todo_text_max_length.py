"""Tests for Todo text maximum length validation (Issue #6340).

These tests verify that:
1. Todo creation rejects text longer than MAX_TEXT_LENGTH (1000 chars)
2. Todo.rename() rejects text longer than MAX_TEXT_LENGTH
3. Error messages clearly state the maximum allowed length
4. Boundary values (exactly MAX_TEXT_LENGTH) work correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


class TestTodoTextMaxLengthValidation:
    """Tests for Todo text maximum length validation."""

    def test_create_todo_with_excessive_text_raises_error(self) -> None:
        """Todo(text) should raise ValueError when text exceeds MAX_TEXT_LENGTH."""
        excessive_text = "a" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match="exceeds maximum"):
            Todo(id=1, text=excessive_text)

    def test_create_todo_with_max_length_text_succeeds(self) -> None:
        """Todo(text) should succeed when text is exactly MAX_TEXT_LENGTH."""
        max_text = "a" * MAX_TEXT_LENGTH
        todo = Todo(id=1, text=max_text)
        assert len(todo.text) == MAX_TEXT_LENGTH
        assert todo.text == max_text

    def test_create_todo_with_normal_text_succeeds(self) -> None:
        """Todo(text) should succeed with normal length text."""
        todo = Todo(id=1, text="Buy milk")
        assert todo.text == "Buy milk"

    def test_rename_with_excessive_text_raises_error(self) -> None:
        """Todo.rename() should raise ValueError when text exceeds MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at
        excessive_text = "b" * (MAX_TEXT_LENGTH + 1)

        with pytest.raises(ValueError, match="exceeds maximum"):
            todo.rename(excessive_text)

        # Verify state unchanged after failed validation
        assert todo.text == "original"
        assert todo.updated_at == original_updated_at

    def test_rename_with_max_length_text_succeeds(self) -> None:
        """Todo.rename() should succeed when text is exactly MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="original")
        max_text = "c" * MAX_TEXT_LENGTH
        todo.rename(max_text)
        assert len(todo.text) == MAX_TEXT_LENGTH
        assert todo.text == max_text

    def test_rename_with_normal_text_succeeds(self) -> None:
        """Todo.rename() should succeed with normal length text."""
        todo = Todo(id=1, text="original")
        todo.rename("new text")
        assert todo.text == "new text"

    def test_error_message_includes_max_length(self) -> None:
        """Error message should include the maximum allowed length."""
        excessive_text = "x" * (MAX_TEXT_LENGTH + 100)
        with pytest.raises(ValueError, match=str(MAX_TEXT_LENGTH)):
            Todo(id=1, text=excessive_text)

    def test_from_dict_rejects_excessive_text(self) -> None:
        """Todo.from_dict() should reject text exceeding MAX_TEXT_LENGTH."""
        excessive_text = "a" * (MAX_TEXT_LENGTH + 1)
        data = {"id": 1, "text": excessive_text}
        with pytest.raises(ValueError, match="exceeds maximum"):
            Todo.from_dict(data)

    def test_from_dict_accepts_max_length_text(self) -> None:
        """Todo.from_dict() should accept text exactly at MAX_TEXT_LENGTH."""
        max_text = "a" * MAX_TEXT_LENGTH
        data = {"id": 1, "text": max_text}
        todo = Todo.from_dict(data)
        assert len(todo.text) == MAX_TEXT_LENGTH
