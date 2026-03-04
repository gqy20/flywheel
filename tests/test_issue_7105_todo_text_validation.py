"""Regression test for issue #7105: Todo.__init__ text type validation.

This test ensures that Todo validates the 'text' parameter type at construction time,
not just in from_dict().
"""

import pytest

from flywheel.todo import Todo


class TestTodoTextValidation:
    """Tests for Todo text field type validation at construction time."""

    def test_todo_with_non_string_text_raises_value_error(self) -> None:
        """Todo(id=1, text=123) should raise ValueError."""
        with pytest.raises(ValueError, match="'text' must be a string"):
            Todo(id=1, text=123)

    def test_todo_with_none_text_raises_value_error(self) -> None:
        """Todo(id=1, text=None) should raise ValueError."""
        with pytest.raises(ValueError, match="'text' must be a string"):
            Todo(id=1, text=None)

    def test_todo_with_valid_string_text_succeeds(self) -> None:
        """Todo(id=1, text='valid') should work correctly."""
        todo = Todo(id=1, text="valid string")
        assert todo.id == 1
        assert todo.text == "valid string"

    def test_todo_with_empty_string_succeeds(self) -> None:
        """Empty string is a valid string type."""
        todo = Todo(id=1, text="")
        assert todo.text == ""
