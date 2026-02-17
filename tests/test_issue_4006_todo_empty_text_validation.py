"""Tests for Todo constructor empty/whitespace text validation (Issue #4006).

These tests verify that:
1. Todo(id=1, text='') raises ValueError
2. Todo(id=1, text='   ') raises ValueError
3. Todo(id=1, text='valid') succeeds
4. Todo.from_dict({'id': 1, 'text': ''}) raises ValueError
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Test suite for Todo empty text validation in constructor."""

    def test_todo_empty_string_raises_value_error(self) -> None:
        """Todo with empty string text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_whitespace_only_raises_value_error(self) -> None:
        """Todo with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_tabs_and_newlines_only_raises_value_error(self) -> None:
        """Todo with tabs/newlines only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n  ")

    def test_todo_valid_text_succeeds(self) -> None:
        """Todo with valid text should be created successfully."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_todo_text_with_surrounding_whitespace_is_trimmed(self) -> None:
        """Todo text with surrounding whitespace should be trimmed."""
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "valid text"

    def test_todo_from_dict_empty_text_raises_value_error(self) -> None:
        """Todo.from_dict with empty text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_todo_from_dict_whitespace_text_raises_value_error(self) -> None:
        """Todo.from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_todo_from_dict_valid_text_succeeds(self) -> None:
        """Todo.from_dict with valid text should succeed."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.text == "valid"
