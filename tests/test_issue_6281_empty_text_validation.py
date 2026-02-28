"""Tests for issue #6281: Todo.__init__ and Todo.from_dict should validate empty text."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoInitEmptyTextValidation:
    """Tests for Todo.__init__ empty text validation (issue #6281)."""

    def test_todo_init_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_init_rejects_whitespace_only(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_init_rejects_tabs_and_newlines(self) -> None:
        """Todo(id=1, text='\t\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n")

    def test_todo_init_accepts_valid_text(self) -> None:
        """Todo(id=1, text='valid') should work normally."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"
        assert todo.id == 1

    def test_todo_init_preserves_text_whitespace(self) -> None:
        """Todo(id=1, text=' valid ') should preserve surrounding whitespace.

        The fix should validate but not auto-strip, similar to rename() behavior.
        """
        todo = Todo(id=1, text=" valid ")
        assert todo.text == " valid "


class TestTodoFromDictEmptyTextValidation:
    """Tests for Todo.from_dict empty text validation (issue #6281)."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tabs_and_newlines(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '\t\n'}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\n"})

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': 'valid'}) should work normally."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.text == "valid"
        assert todo.id == 1

    def test_from_dict_preserves_text_whitespace(self) -> None:
        """Todo.from_dict should preserve surrounding whitespace (not auto-strip)."""
        todo = Todo.from_dict({"id": 1, "text": " valid "})
        assert todo.text == " valid "
