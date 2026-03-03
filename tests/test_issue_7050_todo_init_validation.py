"""Tests for Todo.__init__ text validation (Issue #7050).

These tests verify that:
1. Todo.__init__ rejects empty text strings
2. Todo.__init__ rejects whitespace-only text strings
3. Todo.__init__ strips whitespace and accepts valid text
4. Todo.from_dict also validates text content

This ensures consistency with Todo.rename() which already validates text.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoInitValidation:
    """Tests for Todo.__init__ text validation."""

    def test_todo_init_rejects_empty_string(self) -> None:
        """Bug #7050: Todo.__init__ should reject empty strings."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_init_rejects_whitespace_only_string(self) -> None:
        """Bug #7050: Todo.__init__ should reject whitespace-only strings."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_init_rejects_tabs_and_newlines_only(self) -> None:
        """Bug #7050: Todo.__init__ should reject strings with only whitespace."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n  ")

    def test_todo_init_accepts_valid_text(self) -> None:
        """Bug #7050: Todo.__init__ should still work with valid text."""
        todo = Todo(id=1, text="buy milk")
        assert todo.text == "buy milk"

    def test_todo_init_strips_whitespace(self) -> None:
        """Bug #7050: Todo.__init__ should strip whitespace from text."""
        todo = Todo(id=1, text="  buy milk  ")
        assert todo.text == "buy milk"


class TestTodoFromDictValidation:
    """Tests for Todo.from_dict text validation."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Bug #7050: Todo.from_dict should reject empty text strings."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_string(self) -> None:
        """Bug #7050: Todo.from_dict should reject whitespace-only text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_strips_whitespace(self) -> None:
        """Bug #7050: Todo.from_dict should strip whitespace from text."""
        todo = Todo.from_dict({"id": 1, "text": "  buy milk  "})
        assert todo.text == "buy milk"

    def test_from_dict_accepts_valid_text(self) -> None:
        """Bug #7050: Todo.from_dict should accept valid text."""
        todo = Todo.from_dict({"id": 1, "text": "buy milk"})
        assert todo.text == "buy milk"
