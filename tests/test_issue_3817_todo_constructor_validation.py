"""Regression tests for issue #3817.

Bug: Todo constructor accepts whitespace-only text while rename() rejects it.

The rename() method validates that text is not empty/whitespace-only, but the
constructor does not. This leads to inconsistent behavior where:
- Todo(id=1, text='   ') succeeds
- todo.rename('   ') raises ValueError

This test suite verifies the fix: constructor should validate text like rename().
"""

import pytest

from flywheel.todo import Todo


class TestTodoConstructorTextValidation:
    """Tests for Todo constructor text validation (issue #3817)."""

    def test_whitespace_only_text_raises_value_error(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_tab_newline_whitespace_raises_value_error(self) -> None:
        """Todo(id=1, text='\\t\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n")

    def test_mixed_whitespace_raises_value_error(self) -> None:
        """Todo with only whitespace characters should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t  \n  ")

    def test_valid_text_succeeds(self) -> None:
        """Todo(id=1, text='valid') should work normally."""
        todo = Todo(id=1, text="valid text")
        assert todo.text == "valid text"

    def test_text_with_leading_trailing_whitespace_is_stripped(self) -> None:
        """Todo should strip leading/trailing whitespace from text.

        This matches the behavior of rename() which strips whitespace.
        """
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "valid text"

    def test_empty_string_raises_value_error(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_consistency_with_rename_validation(self) -> None:
        """Constructor and rename() should have consistent validation."""
        # Constructor should reject whitespace-only text
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

        # rename() should also reject whitespace-only text
        todo = Todo(id=1, text="valid")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")
