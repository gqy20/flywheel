"""Tests for empty text validation (Issue #3503).

These tests verify that Todo constructor and from_dict reject empty
or whitespace-only text, consistent with add()/rename() behavior.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorEmptyText:
    """Tests for Todo constructor empty text validation."""

    def test_todo_constructor_rejects_empty_string(self) -> None:
        """Todo constructor should reject empty string."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_constructor_rejects_whitespace_only(self) -> None:
        """Todo constructor should reject whitespace-only string."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_constructor_rejects_tab_newline_whitespace(self) -> None:
        """Todo constructor should reject tab/newline whitespace."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo(id=1, text="\t\n")

    def test_todo_constructor_accepts_valid_text(self) -> None:
        """Todo constructor should accept valid text."""
        todo = Todo(id=1, text="valid task")
        assert todo.text == "valid task"

    def test_todo_constructor_strips_and_accepts_text_with_padding(self) -> None:
        """Todo constructor should strip and accept text with leading/trailing whitespace."""
        todo = Todo(id=1, text="  valid task  ")
        assert todo.text == "valid task"


class TestTodoFromDictEmptyText:
    """Tests for Todo.from_dict empty text validation."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict should reject empty string."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only(self) -> None:
        """Todo.from_dict should reject whitespace-only string."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tab_newline_whitespace(self) -> None:
        """Todo.from_dict should reject tab/newline whitespace."""
        with pytest.raises(ValueError, match=r"text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\n"})

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict should accept valid text."""
        todo = Todo.from_dict({"id": 1, "text": "valid task"})
        assert todo.text == "valid task"

    def test_from_dict_strips_and_accepts_text_with_padding(self) -> None:
        """Todo.from_dict should strip and accept text with leading/trailing whitespace."""
        todo = Todo.from_dict({"id": 1, "text": "  valid task  "})
        assert todo.text == "valid task"
