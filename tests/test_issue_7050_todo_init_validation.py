"""Tests for Todo.__init__ text validation (Issue #7050).

These tests verify that:
1. Todo.__init__ rejects empty string text
2. Todo.__init__ rejects whitespace-only text
3. Todo.__init__ accepts valid text
4. Todo.from_dict rejects empty/whitespace text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoInitTextValidation:
    """Tests for Todo.__init__ text validation."""

    def test_init_with_empty_string_raises_value_error(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_init_with_whitespace_only_raises_value_error(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_init_with_valid_text_succeeds(self) -> None:
        """Todo(id=1, text='valid') should succeed."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_init_strips_whitespace_from_text(self) -> None:
        """Todo.__init__ should strip leading/trailing whitespace."""
        todo = Todo(id=1, text="  hello world  ")
        assert todo.text == "hello world"


class TestTodoFromDictTextValidation:
    """Tests for Todo.from_dict text validation."""

    def test_from_dict_with_empty_string_raises_value_error(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_with_whitespace_only_raises_value_error(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_with_valid_text_succeeds(self) -> None:
        """Todo.from_dict with valid text should succeed."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.text == "valid"
