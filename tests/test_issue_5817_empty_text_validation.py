"""Tests for empty/whitespace-only text validation (Issue #5817).

These tests verify that:
1. Todo construction with empty string raises ValueError
2. Todo.from_dict with empty string raises ValueError
3. Todo.from_dict with whitespace-only string raises ValueError
4. Valid text is still accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Test that empty and whitespace-only text is rejected."""

    def test_todo_construction_empty_string_raises(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match=r"empty|whitespace"):
            Todo(id=1, text="")

    def test_todo_construction_whitespace_only_raises(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match=r"empty|whitespace"):
            Todo(id=1, text="   ")

    def test_todo_from_dict_empty_string_raises(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match=r"empty|whitespace"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_todo_from_dict_whitespace_only_raises(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match=r"empty|whitespace"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_todo_construction_valid_text_works(self) -> None:
        """Todo(id=1, text='valid') should work normally."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_todo_from_dict_valid_text_works(self) -> None:
        """Todo.from_dict with valid text should work normally."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.text == "valid"

    def test_todo_construction_strips_whitespace(self) -> None:
        """Todo should strip leading/trailing whitespace from text."""
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "valid text"

    def test_todo_from_dict_strips_whitespace(self) -> None:
        """Todo.from_dict should strip leading/trailing whitespace from text."""
        todo = Todo.from_dict({"id": 1, "text": "  valid text  "})
        assert todo.text == "valid text"
