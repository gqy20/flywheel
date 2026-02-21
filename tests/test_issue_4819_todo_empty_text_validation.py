"""Regression tests for issue #4819: Todo constructor should validate empty text.

The Todo constructor should reject empty or whitespace-only text strings,
consistent with the validation in rename() method.
"""

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Test that Todo constructor validates text is not empty or whitespace."""

    def test_empty_text_raises_value_error(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="text cannot be empty"):
            Todo(id=1, text="")

    def test_whitespace_only_text_raises_value_error(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="text cannot be empty"):
            Todo(id=1, text="   ")

    def test_whitespace_with_tabs_raises_value_error(self) -> None:
        """Todo(id=1, text='\\t\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="text cannot be empty"):
            Todo(id=1, text="\t\n")

    def test_valid_text_creates_todo(self) -> None:
        """Todo(id=1, text='valid') should create object successfully."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_text_with_leading_trailing_whitespace_is_preserved(self) -> None:
        """Valid text with whitespace should be preserved as-is in constructor.

        Note: rename() method strips whitespace, but constructor behavior
        may differ. For now, we preserve the text as-is.
        """
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "  valid text  "
