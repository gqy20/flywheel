"""Tests for Todo text validation consistency (Issue #3311).

These tests verify that:
1. Todo constructor rejects empty string text (matching rename method behavior)
2. Todo constructor rejects whitespace-only text
3. Todo.from_dict rejects empty string text
4. Valid text is accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorTextValidation:
    """Tests for Todo constructor text validation."""

    def test_constructor_rejects_empty_string_text(self) -> None:
        """Todo constructor should reject empty string text."""
        with pytest.raises(ValueError, match="text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo constructor should reject whitespace-only text."""
        with pytest.raises(ValueError, match="text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_tabs_only_text(self) -> None:
        """Todo constructor should reject tabs-only text."""
        with pytest.raises(ValueError, match="text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_constructor_rejects_newlines_only_text(self) -> None:
        """Todo constructor should reject newlines-only text."""
        with pytest.raises(ValueError, match="text cannot be empty"):
            Todo(id=1, text="\n\n")

    def test_constructor_rejects_mixed_whitespace_text(self) -> None:
        """Todo constructor should reject mixed whitespace text."""
        with pytest.raises(ValueError, match="text cannot be empty"):
            Todo(id=1, text="  \t\n  ")

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo constructor should accept valid text."""
        todo = Todo(id=1, text="buy milk")
        assert todo.text == "buy milk"

    def test_constructor_accepts_text_with_leading_trailing_spaces(self) -> None:
        """Todo constructor should accept text with leading/trailing spaces."""
        # Note: unlike rename(), constructor does NOT strip - it validates as-is
        # The behavior is consistent with rename which first strips, then validates
        # The constructor should strip and validate for consistency
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "  valid text  "


class TestTodoFromDictTextValidation:
    """Tests for Todo.from_dict text validation."""

    def test_from_dict_rejects_empty_string_text(self) -> None:
        """from_dict should reject empty string text."""
        with pytest.raises(ValueError, match="text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """from_dict should reject whitespace-only text."""
        with pytest.raises(ValueError, match="text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_accepts_valid_text(self) -> None:
        """from_dict should accept valid text."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.text == "valid"


class TestRenameMethodConsistency:
    """Tests to verify rename method behavior matches constructor."""

    def test_rename_rejects_empty_string(self) -> None:
        """rename method should reject empty string."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("")

    def test_rename_rejects_whitespace_only(self) -> None:
        """rename method should reject whitespace-only text."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")

    def test_rename_strips_whitespace(self) -> None:
        """rename method should strip whitespace and accept valid text."""
        todo = Todo(id=1, text="original")
        todo.rename("  new text  ")
        assert todo.text == "new text"
