"""Regression tests for issue #6758: Todo constructor text validation.

Tests that Todo constructor validates text field similar to rename():
- Empty text should raise ValueError
- Whitespace-only text should raise ValueError
- Text with leading/trailing whitespace should be stripped
"""

import pytest

from flywheel.todo import Todo


class TestTodoTextValidation:
    """Test Todo constructor text validation (issue #6758)."""

    def test_empty_text_raises_value_error(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_whitespace_only_text_raises_value_error(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError after stripping."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_text_is_stripped_of_whitespace(self) -> None:
        """Todo(id=1, text='  valid  ') should store 'valid' (stripped text)."""
        todo = Todo(id=1, text="  valid  ")
        assert todo.text == "valid"

    def test_valid_text_works_normally(self) -> None:
        """Valid text without extra whitespace should work normally."""
        todo = Todo(id=1, text="buy groceries")
        assert todo.text == "buy groceries"

    def test_tabs_and_newlines_stripped(self) -> None:
        """Whitespace including tabs and newlines should be stripped."""
        todo = Todo(id=1, text="\t\n  task with whitespace  \n\t")
        assert todo.text == "task with whitespace"

    def test_tabs_newlines_only_raises_value_error(self) -> None:
        """Text with only tabs/newlines should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n  \t")
