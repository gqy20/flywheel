"""Tests for Todo empty text validation (Issue #5229).

These tests verify that:
1. Todo constructor rejects whitespace-only text
2. Todo.from_dict() rejects whitespace-only text
3. Valid text with surrounding whitespace is stripped correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Tests for validating that Todo text cannot be empty or whitespace-only."""

    def test_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_newline_tab_whitespace(self) -> None:
        """Todo(id=1, text='\\n\\t') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\n\t")

    def test_constructor_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo(id=1, text='valid') should be created successfully."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_constructor_strips_surrounding_whitespace(self) -> None:
        """Todo(id=1, text='  valid  ') should create todo with stripped text."""
        todo = Todo(id=1, text="  valid  ")
        assert todo.text == "valid"

    def test_constructor_strips_tab_newline_whitespace(self) -> None:
        """Todo should strip leading/trailing tabs and newlines."""
        todo = Todo(id=1, text="\t\nvalid\n\t")
        assert todo.text == "valid"

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tab_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '\\t'}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t"})

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': 'valid'}) should work."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.text == "valid"

    def test_from_dict_strips_surrounding_whitespace(self) -> None:
        """Todo.from_dict should strip surrounding whitespace from text."""
        todo = Todo.from_dict({"id": 1, "text": "  valid  "})
        assert todo.text == "valid"
