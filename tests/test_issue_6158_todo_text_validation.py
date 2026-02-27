"""Tests for Todo text validation (Issue #6158).

These tests verify that:
1. Todo.__init__ rejects empty text
2. Todo.__init__ rejects whitespace-only text
3. Todo.from_dict rejects empty text
4. Todo.from_dict rejects whitespace-only text

This ensures consistency with the rename() method which already validates this.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoTextValidation:
    """Test that Todo validates text field on construction."""

    def test_todo_init_empty_text_raises_value_error(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_init_whitespace_only_text_raises_value_error(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_init_whitespace_only_tab_raises_value_error(self) -> None:
        """Todo(id=1, text='\\t\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n")

    def test_todo_from_dict_empty_text_raises_value_error(self) -> None:
        """Todo.from_dict with empty text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_todo_from_dict_whitespace_only_text_raises_value_error(self) -> None:
        """Todo.from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_todo_init_valid_text_succeeds(self) -> None:
        """Todo with valid text should be created successfully."""
        todo = Todo(id=1, text="buy milk")
        assert todo.text == "buy milk"

    def test_todo_init_text_with_leading_trailing_whitespace_succeeds(self) -> None:
        """Todo should accept text with leading/trailing whitespace (it will be preserved)."""
        todo = Todo(id=1, text="  buy milk  ")
        # Note: __post_init__ may or may not strip - we just verify it doesn't raise
        assert "buy milk" in todo.text
