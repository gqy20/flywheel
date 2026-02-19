"""Tests for whitespace-only text validation (Issue #4494).

These tests verify that whitespace-only text is rejected consistently in:
1. Todo constructor (via __post_init__)
2. Todo.from_dict()
3. Maintaining consistency with rename() and cli.add()
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorWhitespaceValidation:
    """Test Todo constructor rejects whitespace-only text."""

    def test_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo constructor should raise ValueError for whitespace-only text."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_tabs_only_text(self) -> None:
        """Todo constructor should raise ValueError for tabs-only text."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_constructor_rejects_newlines_only_text(self) -> None:
        """Todo constructor should raise ValueError for newlines-only text."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo(id=1, text="\n\n")

    def test_constructor_rejects_mixed_whitespace_text(self) -> None:
        """Todo constructor should raise ValueError for mixed whitespace-only text."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo(id=1, text="  \t\n  ")

    def test_constructor_accepts_valid_text_with_spaces(self) -> None:
        """Todo constructor should accept text with leading/trailing spaces."""
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "  valid text  "

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo constructor should accept valid text."""
        todo = Todo(id=1, text="valid text")
        assert todo.text == "valid text"


class TestTodoFromDictWhitespaceValidation:
    """Test Todo.from_dict rejects whitespace-only text."""

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict should raise ValueError for whitespace-only text."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tabs_only_text(self) -> None:
        """Todo.from_dict should raise ValueError for tabs-only text."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\t"})

    def test_from_dict_rejects_newlines_only_text(self) -> None:
        """Todo.from_dict should raise ValueError for newlines-only text."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\n\n"})

    def test_from_dict_rejects_mixed_whitespace_text(self) -> None:
        """Todo.from_dict should raise ValueError for mixed whitespace-only text."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "  \t\n  "})

    def test_from_dict_accepts_valid_text_with_spaces(self) -> None:
        """Todo.from_dict should accept text with leading/trailing spaces."""
        todo = Todo.from_dict({"id": 1, "text": "  valid text  "})
        assert todo.text == "  valid text  "

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict should accept valid text."""
        todo = Todo.from_dict({"id": 1, "text": "valid text"})
        assert todo.text == "valid text"
