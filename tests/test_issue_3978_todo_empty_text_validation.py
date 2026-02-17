"""Tests for Todo empty text validation (Issue #3978).

These tests verify consistent validation between:
1. Todo constructor (__post_init__)
2. Todo.rename() method
3. Todo.from_dict() class method

The behavior should be consistent: empty or whitespace-only text
should raise ValueError in all cases.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Test that Todo rejects empty or whitespace-only text consistently."""

    def test_constructor_rejects_empty_text(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_tabs_only_text(self) -> None:
        """Todo(id=1, text='\\t\\t') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_constructor_rejects_mixed_whitespace_text(self) -> None:
        """Todo(id=1, text='  \\t  ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t  ")

    def test_from_dict_rejects_empty_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_rename_rejects_empty_text(self) -> None:
        """rename('') should raise ValueError (already implemented)."""
        todo = Todo(id=1, text="valid text")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("")

    def test_rename_rejects_whitespace_only_text(self) -> None:
        """rename('   ') should raise ValueError (already implemented)."""
        todo = Todo(id=1, text="valid text")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo(id=1, text='valid') should work normally."""
        todo = Todo(id=1, text="valid text")
        assert todo.text == "valid text"

    def test_constructor_strips_whitespace_from_text(self) -> None:
        """Todo should strip whitespace from text (consistent with rename behavior)."""
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "valid text"
