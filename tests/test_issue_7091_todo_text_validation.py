"""Test for issue #7091: Todo constructor should validate empty/whitespace text.

This test ensures that Todo constructor and from_dict validate text field
consistently with rename() method - rejecting empty and whitespace-only text.
"""

import pytest

from flywheel.todo import Todo


class TestTodoTextValidation:
    """Test that Todo validates text field on construction."""

    def test_constructor_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_tabs_only(self) -> None:
        """Todo(id=1, text='\\t\\t') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_constructor_rejects_newlines_only(self) -> None:
        """Todo(id=1, text='\\n\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\n\n")

    def test_constructor_rejects_mixed_whitespace(self) -> None:
        """Todo(id=1, text='  \\t\\n  ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t\n  ")

    def test_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict with empty text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only(self) -> None:
        """Todo.from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo with valid text should be created successfully."""
        todo = Todo(id=1, text="Buy groceries")
        assert todo.text == "Buy groceries"

    def test_constructor_accepts_text_with_whitespace(self) -> None:
        """Todo with text containing non-whitespace characters should work."""
        todo = Todo(id=1, text="  Hello World  ")
        assert todo.text == "  Hello World  "

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict with valid text should work."""
        todo = Todo.from_dict({"id": 1, "text": "Buy groceries"})
        assert todo.text == "Buy groceries"
