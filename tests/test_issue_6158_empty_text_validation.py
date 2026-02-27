"""Tests for Todo empty/whitespace text validation (Issue #6158).

These tests verify that:
1. Todo.__init__ rejects empty text
2. Todo.__init__ rejects whitespace-only text
3. Todo.from_dict rejects empty text
4. Todo.from_dict rejects whitespace-only text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Test that Todo rejects empty or whitespace-only text."""

    def test_init_rejects_empty_text(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_init_rejects_whitespace_only_text(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_init_rejects_tab_only_text(self) -> None:
        """Todo(id=1, text='\\t\\t') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_init_rejects_newline_only_text(self) -> None:
        """Todo(id=1, text='\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\n")

    def test_init_rejects_mixed_whitespace_text(self) -> None:
        """Todo(id=1, text='  \\t\\n  ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t\n  ")

    def test_from_dict_rejects_empty_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_init_accepts_valid_text_with_leading_trailing_spaces(self) -> None:
        """Todo should accept text that has content after stripping whitespace."""
        # This should work - text has actual content
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "  valid text  "

    def test_init_accepts_single_character_text(self) -> None:
        """Todo should accept single character text."""
        todo = Todo(id=1, text="a")
        assert todo.text == "a"
