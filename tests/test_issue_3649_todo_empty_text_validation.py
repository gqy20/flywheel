"""Tests for Todo empty text validation (Issue #3649).

These tests verify that:
1. Todo constructor rejects empty/whitespace-only text
2. Todo.from_dict() rejects empty/whitespace-only text
3. Text is stripped of leading/trailing whitespace
4. Validation is consistent with rename() method
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorEmptyTextValidation:
    """Test that Todo constructor validates text is not empty/whitespace."""

    def test_constructor_rejects_empty_text(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo(id=1, text=' ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_tab_only_text(self) -> None:
        """Todo(id=1, text='\\t') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t")

    def test_constructor_rejects_newline_only_text(self) -> None:
        """Todo(id=1, text='\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\n")

    def test_constructor_rejects_mixed_whitespace_only_text(self) -> None:
        """Todo(id=1, text=' \\t\\n ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text=" \t\n ")

    def test_constructor_strips_text(self) -> None:
        """Todo(id=1, text=' valid ') should result in text='valid'."""
        todo = Todo(id=1, text=" valid ")
        assert todo.text == "valid"

    def test_constructor_strips_text_with_tabs(self) -> None:
        """Todo should strip leading/trailing tabs."""
        todo = Todo(id=1, text="\tvalid\t")
        assert todo.text == "valid"

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo should accept valid non-empty text."""
        todo = Todo(id=1, text="buy milk")
        assert todo.text == "buy milk"


class TestTodoFromDictEmptyTextValidation:
    """Test that Todo.from_dict() validates text is not empty/whitespace."""

    def test_from_dict_rejects_empty_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ' '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tab_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '\\t'}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t"})

    def test_from_dict_rejects_newline_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '\\n'}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\n"})

    def test_from_dict_rejects_mixed_whitespace_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ' \\t\\n '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": " \t\n "})

    def test_from_dict_strips_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ' valid '}) should result in text='valid'."""
        todo = Todo.from_dict({"id": 1, "text": " valid "})
        assert todo.text == "valid"

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict should accept valid non-empty text."""
        todo = Todo.from_dict({"id": 1, "text": "buy milk"})
        assert todo.text == "buy milk"


class TestTodoRenameConsistency:
    """Verify rename() still works correctly (should pass unchanged)."""

    def test_rename_rejects_empty_text(self) -> None:
        """rename('') should still raise ValueError."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("")

    def test_rename_rejects_whitespace_only_text(self) -> None:
        """rename(' ') should still raise ValueError."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")

    def test_rename_strips_and_accepts_valid_text(self) -> None:
        """rename(' new ') should work and strip whitespace."""
        todo = Todo(id=1, text="original")
        todo.rename(" new ")
        assert todo.text == "new"
