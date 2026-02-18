"""Tests for empty/whitespace-only text validation (Issue #4256).

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

    def test_constructor_rejects_empty_text(self) -> None:
        """Todo constructor should reject empty text."""
        with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo constructor should reject whitespace-only text."""
        with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_tabs_only_text(self) -> None:
        """Todo constructor should reject tab-only text."""
        with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_constructor_rejects_mixed_whitespace_text(self) -> None:
        """Todo constructor should reject mixed whitespace text."""
        with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
            Todo(id=1, text="  \t  \n  ")

    def test_constructor_preserves_whitespace_in_valid_text(self) -> None:
        """Todo constructor should preserve leading/trailing whitespace in valid text."""
        todo = Todo(id=1, text=" valid text ")
        assert todo.text == " valid text "


class TestTodoFromDictEmptyTextValidation:
    """Tests for Todo.from_dict text validation."""

    def test_from_dict_rejects_empty_text(self) -> None:
        """Todo.from_dict should reject empty text."""
        with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict should reject whitespace-only text."""
        with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tabs_only_text(self) -> None:
        """Todo.from_dict should reject tab-only text."""
        with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\t"})

    def test_from_dict_rejects_mixed_whitespace_text(self) -> None:
        """Todo.from_dict should reject mixed whitespace text."""
        with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "  \t  \n  "})

    def test_from_dict_preserves_whitespace_in_valid_text(self) -> None:
        """Todo.from_dict should preserve leading/trailing whitespace in valid text."""
        todo = Todo.from_dict({"id": 1, "text": " valid text "})
        assert todo.text == " valid text "
