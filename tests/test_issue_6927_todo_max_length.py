"""Tests for Todo text maximum length validation (Issue #6927).

These tests verify that:
1. Todo text is limited to 10000 characters max
2. rename() rejects oversized text
3. from_dict() rejects oversized text
4. Todo creation rejects oversized text
5. Boundary value (10000 chars) works correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo

MAX_TEXT_LENGTH = 10000


class TestTodoTextMaxLength:
    """Tests for Todo text maximum length validation."""

    def test_todo_creation_rejects_oversized_text(self) -> None:
        """Creating a Todo with text > 10000 chars should raise ValueError."""
        oversized_text = "a" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match="cannot exceed"):
            Todo(id=1, text=oversized_text)

    def test_todo_rename_rejects_oversized_text(self) -> None:
        """rename() should reject text > 10000 chars."""
        todo = Todo(id=1, text="valid text")
        oversized_text = "b" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match="cannot exceed"):
            todo.rename(oversized_text)

    def test_todo_from_dict_rejects_oversized_text(self) -> None:
        """from_dict() should reject text > 10000 chars."""
        oversized_text = "c" * (MAX_TEXT_LENGTH + 1)
        data = {"id": 1, "text": oversized_text}
        with pytest.raises(ValueError, match="cannot exceed"):
            Todo.from_dict(data)

    def test_todo_accepts_max_length_text(self) -> None:
        """Todo should accept exactly 10000 characters (boundary value)."""
        max_text = "x" * MAX_TEXT_LENGTH
        # Should not raise
        todo = Todo(id=1, text=max_text)
        assert len(todo.text) == MAX_TEXT_LENGTH

    def test_todo_rename_accepts_max_length_text(self) -> None:
        """rename() should accept exactly 10000 characters (boundary value)."""
        todo = Todo(id=1, text="valid text")
        max_text = "y" * MAX_TEXT_LENGTH
        # Should not raise
        todo.rename(max_text)
        assert len(todo.text) == MAX_TEXT_LENGTH

    def test_todo_from_dict_accepts_max_length_text(self) -> None:
        """from_dict() should accept exactly 10000 characters (boundary value)."""
        max_text = "z" * MAX_TEXT_LENGTH
        data = {"id": 1, "text": max_text}
        # Should not raise
        todo = Todo.from_dict(data)
        assert len(todo.text) == MAX_TEXT_LENGTH

    def test_todo_accepts_normal_length_text(self) -> None:
        """Todo should accept normal length text without issues."""
        normal_text = "This is a normal todo item"
        todo = Todo(id=1, text=normal_text)
        assert todo.text == normal_text

    def test_todo_rename_strips_whitespace_before_length_check(self) -> None:
        """rename() should strip whitespace before checking length."""
        todo = Todo(id=1, text="valid text")
        # Text with leading/trailing whitespace that's still within limit after strip
        text_with_spaces = "  " + "a" * 50 + "  "
        todo.rename(text_with_spaces)
        assert todo.text == "a" * 50
