"""Tests for Issue #3517: Empty/whitespace text validation consistency.

These tests verify that Todo constructor and Todo.from_dict reject empty strings
or whitespace-only strings as 'text', consistent with the rename() method's behavior.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorRejectsEmptyText:
    """Bug #3517: Todo() constructor should reject empty/whitespace text."""

    def test_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_rejects_whitespace_only_spaces(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_rejects_whitespace_only_tabs_newlines(self) -> None:
        """Todo(id=1, text='  \\t\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t\n")

    def test_accepts_valid_text(self) -> None:
        """Todo(id=1, text='valid') should work normally."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"


class TestTodoFromDictRejectsEmptyText:
    """Bug #3517: Todo.from_dict should reject empty/whitespace text."""

    def test_rejects_empty_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_rejects_whitespace_only_spaces(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_rejects_whitespace_only_tabs_newlines(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '  \\t\\n'}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "  \t\n"})

    def test_accepts_valid_text(self) -> None:
        """Todo.from_dict with valid text should work normally."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.text == "valid"
