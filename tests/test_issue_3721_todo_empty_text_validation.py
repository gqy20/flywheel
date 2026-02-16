"""Tests for Todo.__init__ empty text validation (Issue #3721).

These tests verify that:
1. Todo.__init__ validates empty text, consistent with add() and rename()
2. Todo.__init__ validates whitespace-only text
3. Todo.from_dict validates empty text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoInitEmptyTextValidation:
    """Tests for Todo.__init__ validation of empty/whitespace text."""

    def test_todo_init_empty_text_raises_value_error(self) -> None:
        """Todo(id=1, text='') should raise ValueError with message about empty text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_init_whitespace_only_text_raises_value_error(self) -> None:
        """Todo(id=1, text='  \\t  ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t  ")

    def test_todo_init_spaces_only_raises_value_error(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_from_dict_empty_text_raises_value_error(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_todo_from_dict_whitespace_only_raises_value_error(self) -> None:
        """Todo.from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_todo_init_valid_text_works(self) -> None:
        """Todo(id=1, text='valid text') should work normally."""
        todo = Todo(id=1, text="valid text")
        assert todo.text == "valid text"

    def test_todo_init_valid_text_with_leading_trailing_spaces_works(self) -> None:
        """Todo should accept text with spaces that has non-whitespace content."""
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "  valid text  "

    def test_todo_from_dict_valid_text_works(self) -> None:
        """Todo.from_dict with valid text should work normally."""
        todo = Todo.from_dict({"id": 1, "text": "valid text"})
        assert todo.text == "valid text"
