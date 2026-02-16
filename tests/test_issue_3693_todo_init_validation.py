"""Regression tests for issue #3693.

Tests that Todo.__init__ validates text is a non-empty string,
rejecting empty strings and whitespace-only strings.
"""

import pytest

from flywheel.todo import Todo


class TestTodoInitTextValidation:
    """Test that Todo.__init__ rejects empty and whitespace-only text."""

    def test_todo_init_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_init_rejects_whitespace_only_string(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_init_rejects_tabs_and_newlines_only(self) -> None:
        """Todo with only whitespace characters should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n  ")

    def test_todo_init_accepts_valid_text(self) -> None:
        """Todo(id=1, text='valid') should create successfully."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_todo_init_strips_whitespace_from_valid_text(self) -> None:
        """Todo should strip leading/trailing whitespace from valid text."""
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "valid text"
