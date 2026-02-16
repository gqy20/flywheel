"""Tests for Todo empty text validation (Issue #3721).

These tests verify that:
1. Todo.__init__ rejects empty text
2. Todo.__init__ rejects whitespace-only text
3. Todo.from_dict rejects empty text
4. Validation is consistent with add() and rename() behavior
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Test that Todo validates empty text consistently."""

    def test_init_rejects_empty_text(self) -> None:
        """Todo(id=1, text="") should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_init_rejects_whitespace_only_text(self) -> None:
        """Todo(id=1, text="  ") should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_init_rejects_tab_only_text(self) -> None:
        """Todo(id=1, text="\\t") should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t")

    def test_init_rejects_mixed_whitespace_text(self) -> None:
        """Todo(id=1, text=" \\t ") should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text=" \t ")

    def test_from_dict_rejects_empty_text(self) -> None:
        """from_dict with empty text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_init_accepts_valid_text(self) -> None:
        """Todo with valid text should work as expected."""
        todo = Todo(id=1, text="buy milk")
        assert todo.text == "buy milk"

    def test_init_strips_whitespace_from_valid_text(self) -> None:
        """Todo should strip leading/trailing whitespace from text."""
        todo = Todo(id=1, text="  buy milk  ")
        assert todo.text == "buy milk"

    def test_from_dict_accepts_valid_text(self) -> None:
        """from_dict with valid text should work as expected."""
        todo = Todo.from_dict({"id": 1, "text": "buy milk"})
        assert todo.text == "buy milk"

    def test_from_dict_strips_whitespace(self) -> None:
        """from_dict should strip leading/trailing whitespace from text."""
        todo = Todo.from_dict({"id": 1, "text": "  buy milk  "})
        assert todo.text == "buy milk"
