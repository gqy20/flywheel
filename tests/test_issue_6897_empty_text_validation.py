"""Tests for empty text validation (Issue #6897).

These tests verify that:
1. Todo constructor rejects empty string for text field
2. Todo constructor rejects whitespace-only text field
3. Todo.from_dict rejects empty string for text field
4. Existing valid text cases still work
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorEmptyTextValidation:
    """Tests for Todo constructor validation of text field."""

    def test_constructor_rejects_empty_string_text(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo(id=1, text='valid') should succeed."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_constructor_accepts_text_with_leading_trailing_spaces(self) -> None:
        """Todo(id=1, text='  valid  ') should succeed and preserve spaces."""
        todo = Todo(id=1, text="  valid  ")
        # Note: spaces are preserved, not stripped
        assert todo.text == "  valid  "


class TestTodoFromDictEmptyTextValidation:
    """Tests for Todo.from_dict validation of text field."""

    def test_from_dict_rejects_empty_string_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': 'valid'}) should succeed."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.text == "valid"
