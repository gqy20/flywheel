"""Regression test for issue #3311: Todo constructor empty text validation.

This test verifies that the Todo constructor validates empty text strings
to maintain consistency with the rename() method which already validates.
"""

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Tests for Todo constructor empty text validation (issue #3311)."""

    def test_constructor_rejects_empty_string_text(self) -> None:
        """Todo constructor should reject empty string text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo constructor should reject whitespace-only text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo constructor should accept valid text."""
        todo = Todo(id=1, text="valid text")
        assert todo.text == "valid text"

    def test_constructor_strips_whitespace_from_text(self) -> None:
        """Todo constructor should strip whitespace from text (like rename)."""
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "valid text"

    def test_from_dict_rejects_empty_text(self) -> None:
        """from_dict should reject empty text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """from_dict should reject whitespace-only text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_strips_whitespace_from_text(self) -> None:
        """from_dict should strip whitespace from text."""
        todo = Todo.from_dict({"id": 1, "text": "  valid text  "})
        assert todo.text == "valid text"
