"""Tests for Todo empty text validation (Issue #5707).

These tests verify that:
1. Todo.__init__ rejects empty text
2. Todo.__init__ rejects whitespace-only text
3. Todo.from_dict rejects empty/whitespace-only text
4. The behavior is consistent with Todo.rename()
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Tests for validating empty text in Todo constructor."""

    def test_todo_init_rejects_empty_string(self) -> None:
        """Todo(id, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_init_rejects_whitespace_only_text(self) -> None:
        """Todo(id, text='   ') should raise ValueError after stripping."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_init_rejects_tabs_only_text(self) -> None:
        """Todo(id, text='\\t\\t') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_todo_init_rejects_newlines_only_text(self) -> None:
        """Todo(id, text='\\n\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\n\n")

    def test_todo_init_rejects_mixed_whitespace_only_text(self) -> None:
        """Todo(id, text=' \\t\\n ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text=" \t\n ")

    def test_todo_init_accepts_valid_text(self) -> None:
        """Todo(id, text='valid') should work normally."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_todo_init_accepts_text_with_leading_trailing_spaces(self) -> None:
        """Todo(id, text=' valid ') should preserve spaces (rename strips them)."""
        # Note: Unlike rename() which strips, constructor should preserve
        # the text as-is (as long as it's not empty after stripping)
        todo = Todo(id=1, text=" valid ")
        assert todo.text == " valid "

    def test_todo_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_todo_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_todo_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict with valid text should work normally."""
        todo = Todo.from_dict({"id": 1, "text": "buy milk"})
        assert todo.text == "buy milk"

    def test_rename_rejects_empty_string_consistency(self) -> None:
        """rename('') should still raise ValueError (existing behavior)."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("")

    def test_rename_rejects_whitespace_only_consistency(self) -> None:
        """rename('   ') should still raise ValueError (existing behavior)."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")
