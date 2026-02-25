"""Tests for Todo empty text validation (Issue #5707).

These tests verify that:
1. Todo.__init__ rejects empty string text with ValueError
2. Todo.__init__ rejects whitespace-only text with ValueError
3. Todo.from_dict rejects empty text with ValueError
4. Todo.from_dict rejects whitespace-only text with ValueError
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Test that Todo validates text is not empty at construction time."""

    def test_todo_init_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_init_rejects_whitespace_only_text(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError after whitespace stripping."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_init_rejects_tab_only_text(self) -> None:
        """Todo with tab-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_todo_init_rejects_mixed_whitespace_text(self) -> None:
        """Todo with mixed whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t  \n  ")

    def test_todo_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_todo_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_todo_init_accepts_valid_text(self) -> None:
        """Todo should accept valid non-empty text."""
        todo = Todo(id=1, text="valid task")
        assert todo.text == "valid task"

    def test_todo_init_strips_and_accepts_text_with_surrounding_whitespace(self) -> None:
        """Todo should strip whitespace from text and accept if non-empty after stripping."""
        # Based on the rename() behavior, text should be stripped
        todo = Todo(id=1, text="  valid task  ")
        assert todo.text == "valid task"

    def test_todo_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict should accept valid non-empty text."""
        todo = Todo.from_dict({"id": 1, "text": "valid task"})
        assert todo.text == "valid task"
