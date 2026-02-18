"""Tests for Todo empty text validation (Issue #4256).

These tests verify that:
1. Todo constructor rejects empty text
2. Todo constructor rejects whitespace-only text
3. Todo.from_dict rejects empty text
4. Todo.from_dict rejects whitespace-only text
5. Valid text with leading/trailing whitespace is preserved
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorEmptyTextValidation:
    """Tests for Todo constructor text validation."""

    def test_constructor_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_string(self) -> None:
        """Todo(id=1, text=' ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_tab_only_string(self) -> None:
        """Todo(id=1, text='\\t') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t")

    def test_constructor_rejects_newline_only_string(self) -> None:
        """Todo(id=1, text='\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\n")

    def test_constructor_rejects_mixed_whitespace_string(self) -> None:
        """Todo(id=1, text=' \\t\\n ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text=" \t\n ")

    def test_constructor_preserves_whitespace_around_valid_text(self) -> None:
        """Todo(id=1, text=' valid ') should preserve whitespace."""
        todo = Todo(id=1, text=" valid ")
        # Text should be preserved, not auto-stripped
        assert todo.text == " valid "

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo(id=1, text='buy milk') should work normally."""
        todo = Todo(id=1, text="buy milk")
        assert todo.text == "buy milk"


class TestTodoFromDictEmptyTextValidation:
    """Tests for Todo.from_dict text validation."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ' '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tab_only_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '\\t'}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t"})

    def test_from_dict_rejects_newline_only_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '\\n'}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\n"})

    def test_from_dict_rejects_mixed_whitespace_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ' \\t\\n '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": " \t\n "})

    def test_from_dict_preserves_whitespace_around_valid_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ' valid '}) should preserve whitespace."""
        todo = Todo.from_dict({"id": 1, "text": " valid "})
        # Text should be preserved, not auto-stripped
        assert todo.text == " valid "

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': 'buy milk'}) should work normally."""
        todo = Todo.from_dict({"id": 1, "text": "buy milk"})
        assert todo.text == "buy milk"


class TestTodoRenameConsistency:
    """Tests to verify rename() behavior is consistent with constructor."""

    def test_rename_rejects_empty_string(self) -> None:
        """rename('') should raise ValueError (existing behavior)."""
        todo = Todo(id=1, text="valid text")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("")

    def test_rename_rejects_whitespace_only_string(self) -> None:
        """rename(' ') should raise ValueError (existing behavior)."""
        todo = Todo(id=1, text="valid text")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")

    def test_rename_strips_whitespace_from_valid_text(self) -> None:
        """rename(' valid ') should strip whitespace (existing behavior)."""
        todo = Todo(id=1, text="old text")
        todo.rename(" new text ")
        # rename() strips whitespace (this is existing behavior)
        assert todo.text == "new text"
