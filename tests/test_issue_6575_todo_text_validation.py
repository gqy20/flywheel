"""Tests for Todo text validation consistency (Issue #6575).

These tests verify that text validation is consistent across all entry points:
- Todo constructor (__post_init__)
- Todo.from_dict()
- Todo.rename()

All should reject empty or whitespace-only text.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorTextValidation:
    """Test that Todo constructor validates text like rename() does."""

    def test_constructor_rejects_empty_string(self) -> None:
        """Todo constructor should reject empty text string."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only(self) -> None:
        """Todo constructor should reject whitespace-only text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n")

    def test_constructor_strips_and_validates_text(self) -> None:
        """Todo constructor should strip text and reject if empty."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t  ")


class TestTodoFromDictTextValidation:
    """Test that Todo.from_dict() validates text like rename() does."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict() should reject empty text string."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only(self) -> None:
        """Todo.from_dict() should reject whitespace-only text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\n"})


class TestTodoRenameTextValidation:
    """Test that Todo.rename() validates text (existing behavior)."""

    def test_rename_rejects_empty_string(self) -> None:
        """Todo.rename() should reject empty text string."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("")

    def test_rename_rejects_whitespace_only(self) -> None:
        """Todo.rename() should reject whitespace-only text."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")


class TestTodoValidText:
    """Test that valid text is accepted by all entry points."""

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo constructor should accept valid text."""
        todo = Todo(id=1, text="buy milk")
        assert todo.text == "buy milk"

    def test_constructor_strips_whitespace_from_valid_text(self) -> None:
        """Todo constructor should strip whitespace from valid text."""
        todo = Todo(id=1, text="  buy milk  ")
        assert todo.text == "buy milk"

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict() should accept valid text."""
        todo = Todo.from_dict({"id": 1, "text": "buy milk"})
        assert todo.text == "buy milk"

    def test_from_dict_strips_whitespace_from_valid_text(self) -> None:
        """Todo.from_dict() should strip whitespace from valid text."""
        todo = Todo.from_dict({"id": 1, "text": "  buy milk  "})
        assert todo.text == "buy milk"

    def test_rename_accepts_valid_text(self) -> None:
        """Todo.rename() should accept valid text."""
        todo = Todo(id=1, text="original")
        todo.rename("new text")
        assert todo.text == "new text"

    def test_rename_strips_whitespace_from_valid_text(self) -> None:
        """Todo.rename() should strip whitespace from valid text."""
        todo = Todo(id=1, text="original")
        todo.rename("  new text  ")
        assert todo.text == "new text"
