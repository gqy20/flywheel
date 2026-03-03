"""Tests for issue #6897: Todo constructor and from_dict empty text validation.

Bug: Todo constructor and from_dict accept empty string for text field, but rename()
rejects it - inconsistent validation.

Acceptance criteria:
- Todo(id=1, text='') raises ValueError with message 'Todo text cannot be empty'
- Todo(id=1, text='   ') raises ValueError with message 'Todo text cannot be empty'
- Todo.from_dict({'id': 1, 'text': ''}) raises ValueError
- Existing valid text cases still work
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorEmptyTextValidation:
    """Test that Todo constructor rejects empty/whitespace-only text."""

    def test_todo_constructor_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_constructor_rejects_whitespace_only(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_constructor_rejects_tabs_and_newlines(self) -> None:
        """Todo(id=1, text='\\t\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n")

    def test_todo_constructor_accepts_valid_text(self) -> None:
        """Todo(id=1, text='valid') should succeed."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_todo_constructor_strips_whitespace_from_valid_text(self) -> None:
        """Todo constructor should strip whitespace and validate."""
        # This should strip and accept the text
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "valid text"


class TestTodoFromDictEmptyTextValidation:
    """Test that Todo.from_dict rejects empty/whitespace-only text."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tabs_and_newlines(self) -> None:
        """Todo.from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\n"})

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict with valid text should succeed."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.text == "valid"

    def test_from_dict_strips_whitespace_from_valid_text(self) -> None:
        """Todo.from_dict should strip whitespace and validate."""
        todo = Todo.from_dict({"id": 1, "text": "  valid text  "})
        assert todo.text == "valid text"
