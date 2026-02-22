"""Tests for Todo constructor empty text validation (Issue #5229).

These tests verify that:
1. Todo constructor rejects text that is only whitespace
2. Todo constructor trims leading/trailing whitespace from valid text
3. Todo.from_dict also validates text for whitespace-only values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Test suite for empty text validation in Todo constructor."""

    def test_todo_constructor_rejects_whitespace_only_text_spaces(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_constructor_rejects_whitespace_only_text_tabs_newlines(self) -> None:
        """Todo(id=1, text='\\n\\t') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\n\t")

    def test_todo_constructor_rejects_whitespace_only_text_mixed(self) -> None:
        """Todo(id=1, text=' \\n \\t ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text=" \n \t ")

    def test_todo_constructor_accepts_valid_text(self) -> None:
        """Todo(id=1, text='valid') should create normally."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_todo_constructor_trims_whitespace_and_creates(self) -> None:
        """Todo(id=1, text='  valid  ') should create with trimmed text 'valid'."""
        todo = Todo(id=1, text="  valid  ")
        assert todo.text == "valid"

    def test_todo_from_dict_rejects_whitespace_only_text_tabs(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '\\t'}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t"})

    def test_todo_from_dict_rejects_whitespace_only_text_spaces(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_todo_from_dict_trims_whitespace_and_creates(self) -> None:
        """Todo.from_dict should trim whitespace and create todo with clean text."""
        todo = Todo.from_dict({"id": 1, "text": "  valid  "})
        assert todo.text == "valid"
