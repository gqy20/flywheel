"""Tests for issue #4256: Todo constructor and from_dict text validation."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorTextValidation:
    """Test that Todo constructor validates text is not empty or whitespace-only."""

    def test_constructor_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError after whitespace stripping."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_tabs_and_newlines(self) -> None:
        """Todo(id=1, text='\\t\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n")

    def test_constructor_preserves_whitespace_on_valid_text(self) -> None:
        """Todo(id=1, text=' valid ') should preserve whitespace on construction."""
        todo = Todo(id=1, text=" valid ")
        # Whitespace should be preserved (not auto-stripped on construction)
        # This is different from rename() which strips whitespace
        assert todo.text == " valid "


class TestTodoFromDictTextValidation:
    """Test that Todo.from_dict validates text is not empty or whitespace-only."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tabs_and_newlines(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '\\t\\n'}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\n"})

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict with valid text should work."""
        todo = Todo.from_dict({"id": 1, "text": "valid todo"})
        assert todo.text == "valid todo"
