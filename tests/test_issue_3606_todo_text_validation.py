"""Tests for issue #3606: Todo constructor text validation."""

import pytest

from flywheel.todo import Todo


class TestTodoTextValidation:
    """Test that Todo constructor rejects empty or whitespace-only text."""

    def test_empty_text_raises_value_error(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_whitespace_only_text_raises_value_error(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_tab_only_text_raises_value_error(self) -> None:
        """Todo(id=1, text='\\t\\t') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_newline_only_text_raises_value_error(self) -> None:
        """Todo(id=1, text='\\n\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\n\n")

    def test_mixed_whitespace_only_text_raises_value_error(self) -> None:
        """Todo(id=1, text='  \\t\\n  ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t\n  ")

    def test_valid_text_succeeds(self) -> None:
        """Todo(id=1, text='valid') should succeed."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_text_with_leading_trailing_whitespace_succeeds(self) -> None:
        """Todo preserves text with leading/trailing whitespace (rename strips it)."""
        todo = Todo(id=1, text="  valid  ")
        assert todo.text == "  valid  "

    def test_from_dict_empty_text_raises_value_error(self) -> None:
        """from_dict with empty text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_whitespace_only_raises_value_error(self) -> None:
        """from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})
