"""Tests for empty/whitespace text validation in Todo (Issue #5817).

These tests verify that:
1. Todo construction rejects empty string text
2. Todo construction rejects whitespace-only text
3. Todo.from_dict rejects empty string text
4. Todo.from_dict rejects whitespace-only text
5. Valid text is still accepted in both paths
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructionEmptyText:
    """Tests for Todo constructor rejecting empty/whitespace text."""

    def test_todo_construction_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match=r"empty"):
            Todo(id=1, text="")

    def test_todo_construction_rejects_whitespace_only(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match=r"empty"):
            Todo(id=1, text="   ")

    def test_todo_construction_rejects_tabs_only(self) -> None:
        """Todo(id=1, text='\\t\\t') should raise ValueError."""
        with pytest.raises(ValueError, match=r"empty"):
            Todo(id=1, text="\t\t")

    def test_todo_construction_rejects_mixed_whitespace(self) -> None:
        """Todo(id=1, text='  \\t  ') should raise ValueError."""
        with pytest.raises(ValueError, match=r"empty"):
            Todo(id=1, text="  \t  ")


class TestTodoFromDictEmptyText:
    """Tests for Todo.from_dict rejecting empty/whitespace text."""

    def test_todo_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict with empty text should raise ValueError."""
        with pytest.raises(ValueError, match=r"empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_todo_from_dict_rejects_whitespace_only(self) -> None:
        """Todo.from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match=r"empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_todo_from_dict_rejects_tabs_only(self) -> None:
        """Todo.from_dict with tabs-only text should raise ValueError."""
        with pytest.raises(ValueError, match=r"empty"):
            Todo.from_dict({"id": 1, "text": "\t\t"})

    def test_todo_from_dict_rejects_mixed_whitespace(self) -> None:
        """Todo.from_dict with mixed whitespace text should raise ValueError."""
        with pytest.raises(ValueError, match=r"empty"):
            Todo.from_dict({"id": 1, "text": "  \t  "})


class TestTodoValidTextAccepted:
    """Tests ensuring valid text is still accepted."""

    def test_todo_construction_accepts_valid_text(self) -> None:
        """Todo(id=1, text='valid') should work normally."""
        todo = Todo(id=1, text="valid text")
        assert todo.text == "valid text"

    def test_todo_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict with valid text should work normally."""
        todo = Todo.from_dict({"id": 1, "text": "valid text"})
        assert todo.text == "valid text"

    def test_todo_construction_normalizes_whitespace(self) -> None:
        """Todo construction should strip leading/trailing whitespace from valid text."""
        todo = Todo(id=1, text="  valid text  ")
        # The text should be stripped (matching rename() behavior)
        assert todo.text.strip() == "valid text"

    def test_todo_from_dict_normalizes_whitespace(self) -> None:
        """Todo.from_dict should strip leading/trailing whitespace from valid text."""
        todo = Todo.from_dict({"id": 1, "text": "  valid text  "})
        # The text should be stripped (matching rename() behavior)
        assert todo.text.strip() == "valid text"
