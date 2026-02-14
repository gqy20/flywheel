"""Tests for Todo constructor text validation (Issue #3378).

These tests verify that Todo constructor validates the text field:
1. Rejects None for text field
2. Rejects empty strings for text field
3. Rejects whitespace-only strings for text field
4. Error message matches rename() validation message
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorTextValidation:
    """Tests for Todo constructor text validation."""

    def test_constructor_rejects_none_for_text(self) -> None:
        """Todo constructor should reject None for text field."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text=None)  # type: ignore[arg-type]

    def test_constructor_rejects_empty_string_for_text(self) -> None:
        """Todo constructor should reject empty string for text field."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_for_text(self) -> None:
        """Todo constructor should reject whitespace-only string for text field."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo constructor should accept valid non-empty text."""
        todo = Todo(id=1, text="buy milk")
        assert todo.text == "buy milk"

    def test_constructor_strips_whitespace_from_text(self) -> None:
        """Todo constructor should strip whitespace from text like rename()."""
        todo = Todo(id=1, text="  buy milk  ")
        assert todo.text == "buy milk"

    def test_error_message_matches_rename_validation(self) -> None:
        """Constructor validation message should match rename() message."""
        # Test that both use the same error message
        todo = Todo(id=1, text="valid")

        # rename() raises this message
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("")

        # constructor should raise the same message
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=2, text="")
