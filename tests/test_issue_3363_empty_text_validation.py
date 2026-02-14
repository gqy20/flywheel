"""Tests for Todo empty text validation (Issue #3363).

These tests verify that:
1. Todo.__init__ rejects empty text strings (consistent with rename())
2. Todo.__init__ rejects whitespace-only text strings
3. Todo.from_dict rejects empty/whitespace-only text strings
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Test that Todo validates text is not empty/whitespace-only."""

    def test_todo_init_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_init_rejects_whitespace_only_string(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError for whitespace-only text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_init_rejects_whitespace_with_tabs_and_newlines(self) -> None:
        """Todo(id=1, text='  \\t\\n  ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t\n  ")

    def test_todo_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict with empty text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_todo_from_dict_rejects_whitespace_only_string(self) -> None:
        """Todo.from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_todo_init_accepts_valid_text(self) -> None:
        """Todo should accept valid non-empty text."""
        todo = Todo(id=1, text="buy milk")
        assert todo.text == "buy milk"

    def test_todo_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict should accept valid non-empty text."""
        todo = Todo.from_dict({"id": 1, "text": "buy milk"})
        assert todo.text == "buy milk"

    def test_rename_rejects_empty_string(self) -> None:
        """rename('') should still raise ValueError (existing behavior)."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("")

    def test_rename_rejects_whitespace_only_string(self) -> None:
        """rename('   ') should still raise ValueError (existing behavior)."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")
