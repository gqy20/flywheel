"""Tests for Issue #3158: Validate text in constructor and from_dict.

These tests verify that Todo constructor and from_dict reject empty/whitespace-only
text, matching the behavior of rename().

Bug: Todo constructor and from_dict allow empty/whitespace-only text while
rename() rejects it.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorTextValidation:
    """Tests for Todo constructor text validation (Issue #3158)."""

    def test_constructor_rejects_empty_string(self) -> None:
        """Todo constructor should reject empty string for text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only(self) -> None:
        """Todo constructor should reject whitespace-only string for text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text=" ")

    def test_constructor_rejects_tab_newline_whitespace(self) -> None:
        """Todo constructor should reject tab/newline whitespace for text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n")

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo constructor should accept valid non-empty text."""
        todo = Todo(id=1, text="valid text")
        assert todo.text == "valid text"

    def test_constructor_strips_whitespace(self) -> None:
        """Todo constructor should strip leading/trailing whitespace from text."""
        todo = Todo(id=1, text="  padded text  ")
        assert todo.text == "padded text"


class TestTodoFromDictTextValidation:
    """Tests for Todo.from_dict text validation (Issue #3158)."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict should reject empty string for text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only(self) -> None:
        """Todo.from_dict should reject whitespace-only string for text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": " "})

    def test_from_dict_rejects_tab_newline_whitespace(self) -> None:
        """Todo.from_dict should reject tab/newline whitespace for text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\n"})

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict should accept valid non-empty text."""
        todo = Todo.from_dict({"id": 1, "text": "valid text"})
        assert todo.text == "valid text"

    def test_from_dict_strips_whitespace(self) -> None:
        """Todo.from_dict should strip leading/trailing whitespace from text."""
        todo = Todo.from_dict({"id": 1, "text": "  padded text  "})
        assert todo.text == "padded text"
