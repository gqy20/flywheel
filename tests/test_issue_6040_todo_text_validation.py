"""Tests for Todo text validation in __init__ (Issue #6040).

These tests verify that:
1. Todo.__init__ rejects empty text (consistent with rename())
2. Todo.__init__ rejects whitespace-only text
3. Todo.from_dict also validates text for empty/whitespace
4. Valid text is still accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoTextValidation:
    """Tests for Todo text validation in __init__ and from_dict."""

    def test_todo_init_rejects_empty_text(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_init_rejects_whitespace_only_text(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_init_rejects_tab_newline_whitespace(self) -> None:
        """Todo(id=1, text='  \\t\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t\n")

    def test_todo_init_accepts_valid_text(self) -> None:
        """Todo(id=1, text='valid text') should succeed."""
        todo = Todo(id=1, text="valid text")
        assert todo.text == "valid text"

    def test_todo_init_accepts_text_with_leading_trailing_spaces(self) -> None:
        """Todo with valid content but leading/trailing spaces should succeed."""
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "  valid text  "

    def test_todo_from_dict_rejects_empty_text(self) -> None:
        """Todo.from_dict with empty text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_todo_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_todo_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict with valid text should succeed."""
        todo = Todo.from_dict({"id": 1, "text": "valid text"})
        assert todo.text == "valid text"
