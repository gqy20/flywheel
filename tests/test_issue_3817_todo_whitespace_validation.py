"""Tests for Todo constructor whitespace validation (Issue #3817).

These tests verify that:
1. Todo constructor rejects whitespace-only text (consistent with rename())
2. Todo constructor accepts valid text
3. Error message matches rename() behavior
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorWhitespaceValidation:
    """Test that Todo constructor validates text consistently with rename()."""

    def test_todo_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_constructor_rejects_tab_newline_whitespace(self) -> None:
        """Todo(id=1, text='\\t\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n")

    def test_todo_constructor_rejects_empty_text(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_constructor_accepts_valid_text(self) -> None:
        """Todo(id=1, text='valid text') should work normally."""
        todo = Todo(id=1, text="valid text")
        assert todo.text == "valid text"

    def test_todo_constructor_strips_whitespace_from_valid_text(self) -> None:
        """Todo constructor should strip whitespace from valid text (like rename())."""
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "valid text"

    def test_todo_rename_rejects_whitespace_only_text(self) -> None:
        """rename() should still reject whitespace-only text."""
        todo = Todo(id=1, text="valid text")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")

    def test_consistency_between_constructor_and_rename(self) -> None:
        """Constructor and rename() should have consistent error messages."""
        import re

        # Get error from constructor
        constructor_error = None
        try:
            Todo(id=1, text="   ")
        except ValueError as e:
            constructor_error = str(e)

        # Get error from rename()
        rename_error = None
        try:
            todo = Todo(id=1, text="valid")
            todo.rename("   ")
        except ValueError as e:
            rename_error = str(e)

        # Both should raise the same error
        assert constructor_error == rename_error
        assert "cannot be empty" in constructor_error.lower()
