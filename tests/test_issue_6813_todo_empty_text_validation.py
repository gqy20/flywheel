"""Tests for Todo empty text validation (Issue #6813).

These tests verify that:
1. Todo constructor rejects empty text with ValueError
2. Todo constructor rejects whitespace-only text with ValueError
3. Todo.from_dict rejects empty text with ValueError
4. Valid text is accepted normally
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Tests for validating that Todo text cannot be empty."""

    def test_empty_text_raises_value_error(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_whitespace_only_text_raises_value_error(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_tabs_only_text_raises_value_error(self) -> None:
        """Todo(id=1, text='\\t\\t') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_mixed_whitespace_text_raises_value_error(self) -> None:
        """Todo(id=1, text='  \\t  ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t  ")

    def test_valid_text_succeeds(self) -> None:
        """Todo(id=1, text='valid') should succeed."""
        todo = Todo(id=1, text="valid text")
        assert todo.text == "valid text"

    def test_valid_text_with_leading_trailing_spaces_succeeds(self) -> None:
        """Todo(id=1, text='  valid  ') should preserve text as-is."""
        # Note: unlike rename(), constructor preserves original text including spaces
        todo = Todo(id=1, text="  valid  ")
        assert todo.text == "  valid  "

    def test_from_dict_empty_text_raises_value_error(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_whitespace_only_raises_value_error(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_valid_text_succeeds(self) -> None:
        """Todo.from_dict with valid text should succeed."""
        todo = Todo.from_dict({"id": 1, "text": "valid text"})
        assert todo.text == "valid text"
