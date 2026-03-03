"""Tests for empty text validation (Issue #6897).

These tests verify that:
1. Todo constructor rejects empty string for text field
2. Todo constructor rejects whitespace-only text
3. Todo.from_dict rejects empty string for text field
4. Todo.from_dict rejects whitespace-only text
5. Existing valid text cases still work
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorEmptyTextValidation:
    """Tests for Todo constructor empty text validation."""

    def test_todo_constructor_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_constructor_rejects_whitespace_only(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_constructor_rejects_tabs_only(self) -> None:
        """Todo(id=1, text='\\t\\t') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_todo_constructor_rejects_newlines_only(self) -> None:
        """Todo(id=1, text='\\n\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\n\n")

    def test_todo_constructor_rejects_mixed_whitespace(self) -> None:
        """Todo(id=1, text='  \\t  \\n  ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t  \n  ")

    def test_todo_constructor_accepts_valid_text(self) -> None:
        """Todo(id=1, text='valid') should succeed."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_todo_constructor_strips_whitespace_from_valid_text(self) -> None:
        """Todo constructor should strip whitespace from valid text."""
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "valid text"


class TestTodoFromDictEmptyTextValidation:
    """Tests for Todo.from_dict empty text validation."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tabs_only(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '\\t\\t'}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\t"})

    def test_from_dict_rejects_newlines_only(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '\\n\\n'}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\n\n"})

    def test_from_dict_rejects_mixed_whitespace(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '  \\t  \\n  '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "  \t  \n  "})

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': 'valid'}) should succeed."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.text == "valid"

    def test_from_dict_strips_whitespace_from_valid_text(self) -> None:
        """Todo.from_dict should strip whitespace from valid text."""
        todo = Todo.from_dict({"id": 1, "text": "  valid text  "})
        assert todo.text == "valid text"


class TestTodoRenameConsistency:
    """Tests to ensure rename() validation is consistent with constructor."""

    def test_rename_rejects_empty_string(self) -> None:
        """rename('') should raise ValueError."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("")

    def test_rename_rejects_whitespace_only(self) -> None:
        """rename('   ') should raise ValueError."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")

    def test_rename_accepts_valid_text(self) -> None:
        """rename('valid') should succeed."""
        todo = Todo(id=1, text="original")
        todo.rename("valid")
        assert todo.text == "valid"

    def test_rename_strips_whitespace(self) -> None:
        """rename should strip whitespace."""
        todo = Todo(id=1, text="original")
        todo.rename("  new text  ")
        assert todo.text == "new text"
