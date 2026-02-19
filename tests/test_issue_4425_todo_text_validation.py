"""Tests for Todo text validation on construction (Issue #4425).

These tests verify that:
1. Todo constructor strips and validates text (not just rename())
2. Todo.from_dict strips and validates text
3. Whitespace-only text raises ValueError
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorValidation:
    """Tests for Todo() constructor text validation."""

    def test_todo_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo(id=1, text='  ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  ")

    def test_todo_constructor_rejects_empty_text(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_constructor_rejects_whitespace_only_various(self) -> None:
        """Todo should reject various whitespace-only strings."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n")

        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   \n   ")

    def test_todo_constructor_strips_padded_text(self) -> None:
        """Todo(id=1, text='  padded  ') should store 'padded'."""
        todo = Todo(id=1, text="  padded  ")
        assert todo.text == "padded"

    def test_todo_constructor_strips_leading_whitespace(self) -> None:
        """Todo should strip leading whitespace from text."""
        todo = Todo(id=1, text="   leading")
        assert todo.text == "leading"

    def test_todo_constructor_strips_trailing_whitespace(self) -> None:
        """Todo should strip trailing whitespace from text."""
        todo = Todo(id=1, text="trailing   ")
        assert todo.text == "trailing"

    def test_todo_constructor_preserves_internal_whitespace(self) -> None:
        """Todo should preserve internal whitespace."""
        todo = Todo(id=1, text="  hello world  ")
        assert todo.text == "hello world"


class TestTodoFromDictValidation:
    """Tests for Todo.from_dict() text validation."""

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '  '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "  "})

    def test_from_dict_rejects_empty_text(self) -> None:
        """Todo.from_dict with empty text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_strips_and_accepts_padded_text(self) -> None:
        """Todo.from_dict should strip padded text and accept it."""
        todo = Todo.from_dict({"id": 1, "text": "  padded  "})
        assert todo.text == "padded"

    def test_from_dict_strips_leading_whitespace(self) -> None:
        """Todo.from_dict should strip leading whitespace."""
        todo = Todo.from_dict({"id": 1, "text": "   leading"})
        assert todo.text == "leading"

    def test_from_dict_strips_trailing_whitespace(self) -> None:
        """Todo.from_dict should strip trailing whitespace."""
        todo = Todo.from_dict({"id": 1, "text": "trailing   "})
        assert todo.text == "trailing"
