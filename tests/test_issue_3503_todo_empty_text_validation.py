"""Test for issue #3503: Todo should reject empty or whitespace-only text.

This test verifies that Todo constructor and from_dict reject empty or
whitespace-only text, consistent with add()/rename() behavior.
"""

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Test that Todo validates text is not empty or whitespace-only."""

    def test_constructor_rejects_empty_string(self):
        """Todo constructor should reject empty string for text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only(self):
        """Todo constructor should reject whitespace-only text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_tabs_and_newlines(self):
        """Todo constructor should reject text with only tabs and newlines."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n  \r\n")

    def test_from_dict_rejects_empty_string(self):
        """Todo.from_dict should reject empty string for text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only(self):
        """Todo.from_dict should reject whitespace-only text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tabs_and_newlines(self):
        """Todo.from_dict should reject text with only tabs and newlines."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\n  \r\n"})

    def test_constructor_accepts_stripped_text(self):
        """Todo constructor should accept valid text with leading/trailing spaces."""
        # Text with leading/trailing whitespace should be stripped and accepted
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "valid text"

    def test_from_dict_accepts_stripped_text(self):
        """Todo.from_dict should accept valid text with leading/trailing spaces."""
        # Text with leading/trailing whitespace should be stripped and accepted
        todo = Todo.from_dict({"id": 1, "text": "  valid text  "})
        assert todo.text == "valid text"
