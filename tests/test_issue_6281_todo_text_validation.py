"""Tests for Todo text validation (Issue #6281).

These tests verify that Todo.__init__ and Todo.from_dict validate
that the text field is not empty or whitespace-only.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoInitTextValidation:
    """Tests for Todo.__init__ text validation."""

    def test_init_rejects_empty_text(self) -> None:
        """Todo.__init__ should reject empty text string."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo(id=1, text="")

    def test_init_rejects_whitespace_only_text(self) -> None:
        """Todo.__init__ should reject text that is only whitespace."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo(id=1, text="   ")

    def test_init_accepts_valid_text(self) -> None:
        """Todo.__init__ should accept valid text."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_init_preserves_whitespace_around_valid_text(self) -> None:
        """Todo.__init__ should preserve whitespace around valid text."""
        todo = Todo(id=1, text=" valid ")
        assert todo.text == " valid "


class TestTodoFromDictTextValidation:
    """Tests for Todo.from_dict text validation."""

    def test_from_dict_rejects_empty_text(self) -> None:
        """Todo.from_dict should reject empty text string."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict should reject text that is only whitespace."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict should accept valid text."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.text == "valid"

    def test_from_dict_preserves_whitespace_around_valid_text(self) -> None:
        """Todo.from_dict should preserve whitespace around valid text."""
        todo = Todo.from_dict({"id": 1, "text": " valid "})
        assert todo.text == " valid "
