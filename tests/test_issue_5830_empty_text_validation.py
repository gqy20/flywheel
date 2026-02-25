"""Tests for empty/whitespace text validation (Issue #5830).

These tests verify that:
1. Todo.__init__ rejects empty text strings
2. Todo.__init__ rejects whitespace-only text strings
3. Todo.from_dict rejects empty text strings
4. Todo.from_dict rejects whitespace-only text strings
5. Behavior is consistent with rename() method
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoInitRejectsEmptyText:
    """Tests for Todo.__init__ rejecting empty/whitespace text."""

    def test_init_rejects_empty_string_text(self) -> None:
        """Todo.__init__ should reject empty string as text."""
        with pytest.raises(ValueError, match=r"(?i)todo text cannot be empty"):
            Todo(id=1, text="")

    def test_init_rejects_whitespace_only_text(self) -> None:
        """Todo.__init__ should reject whitespace-only string as text."""
        with pytest.raises(ValueError, match=r"(?i)todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_init_rejects_tabs_only_text(self) -> None:
        """Todo.__init__ should reject tabs-only string as text."""
        with pytest.raises(ValueError, match=r"(?i)todo text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_init_rejects_mixed_whitespace_text(self) -> None:
        """Todo.__init__ should reject mixed whitespace string as text."""
        with pytest.raises(ValueError, match=r"(?i)todo text cannot be empty"):
            Todo(id=1, text="  \t  \n  ")


class TestTodoFromDictRejectsEmptyText:
    """Tests for Todo.from_dict rejecting empty/whitespace text."""

    def test_from_dict_rejects_empty_string_text(self) -> None:
        """Todo.from_dict should reject empty string as text."""
        with pytest.raises(ValueError, match=r"(?i)todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict should reject whitespace-only string as text."""
        with pytest.raises(ValueError, match=r"(?i)todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tabs_only_text(self) -> None:
        """Todo.from_dict should reject tabs-only string as text."""
        with pytest.raises(ValueError, match=r"(?i)todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\t"})

    def test_from_dict_rejects_mixed_whitespace_text(self) -> None:
        """Todo.from_dict should reject mixed whitespace string as text."""
        with pytest.raises(ValueError, match=r"(?i)todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "  \t  \n  "})


class TestTodoAcceptsValidText:
    """Tests for Todo accepting valid text (regression tests)."""

    def test_init_accepts_non_empty_text(self) -> None:
        """Todo.__init__ should accept non-empty text."""
        todo = Todo(id=1, text="Buy groceries")
        assert todo.text == "Buy groceries"

    def test_init_accepts_text_with_leading_trailing_whitespace(self) -> None:
        """Todo.__init__ should accept text that has whitespace but real content."""
        todo = Todo(id=1, text="  Buy groceries  ")
        assert todo.text == "  Buy groceries  "

    def test_from_dict_accepts_non_empty_text(self) -> None:
        """Todo.from_dict should accept non-empty text."""
        todo = Todo.from_dict({"id": 1, "text": "Buy groceries"})
        assert todo.text == "Buy groceries"
