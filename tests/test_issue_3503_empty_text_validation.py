"""Tests for issue #3503: Todo constructor and from_dict should reject empty/whitespace text.

This ensures consistency with Todo.rename() and TodoApp.add() which already
validate that text is not empty or whitespace-only.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorEmptyText:
    """Tests for Todo constructor rejecting empty/whitespace text."""

    def test_constructor_rejects_empty_string(self) -> None:
        """Bug #3503: Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_space(self) -> None:
        """Bug #3503: Todo(id=1, text=' ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text=" ")

    def test_constructor_rejects_whitespace_only_tab_newline(self) -> None:
        """Bug #3503: Todo(id=1, text='\\t\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n")

    def test_constructor_accepts_valid_text(self) -> None:
        """Bug #3503: Todo(id=1, text='valid') should work normally."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"


class TestTodoFromDictEmptyText:
    """Tests for Todo.from_dict() rejecting empty/whitespace text."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Bug #3503: Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_space(self) -> None:
        """Bug #3503: Todo.from_dict({'id': 1, 'text': ' '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": " "})

    def test_from_dict_rejects_whitespace_only_tab_newline(self) -> None:
        """Bug #3503: Todo.from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\n"})

    def test_from_dict_accepts_valid_text(self) -> None:
        """Bug #3503: Todo.from_dict with valid text should work normally."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.text == "valid"
