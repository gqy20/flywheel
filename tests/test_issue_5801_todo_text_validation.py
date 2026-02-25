"""Tests for issue #5801: Todo text validation on construction.

Bug: Todo text is not stripped/validated on construction, allowing
whitespace-only or empty text via direct instantiation.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructionTextValidation:
    """Tests for Todo text validation during construction."""

    def test_todo_construction_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_construction_rejects_whitespace_only_spaces(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_construction_rejects_whitespace_only_tabs_newlines(self) -> None:
        """Todo(id=1, text='\\t\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n")

    def test_todo_construction_strips_whitespace_from_valid_text(self) -> None:
        """Todo(id=1, text='  valid  ') should store stripped text 'valid'."""
        todo = Todo(id=1, text="  valid  ")
        assert todo.text == "valid"

    def test_todo_construction_preserves_internal_whitespace(self) -> None:
        """Todo should preserve whitespace within valid text."""
        todo = Todo(id=1, text="  hello world  ")
        assert todo.text == "hello world"

    def test_todo_from_dict_rejects_empty_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_todo_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_todo_from_dict_strips_whitespace_from_valid_text(self) -> None:
        """Todo.from_dict should strip whitespace from valid text."""
        todo = Todo.from_dict({"id": 1, "text": "  valid  "})
        assert todo.text == "valid"
