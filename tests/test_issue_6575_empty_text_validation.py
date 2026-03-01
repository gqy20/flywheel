"""Tests for Issue #6575: Consistent empty text validation across all Todo entry points.

These tests verify that:
1. Todo constructor rejects empty/whitespace text
2. Todo.from_dict() rejects empty/whitespace text
3. Todo.rename() rejects empty/whitespace text (already implemented)

All entry points should enforce the same validation rules.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorEmptyTextValidation:
    """Tests for Todo constructor text validation (Issue #6575)."""

    def test_constructor_rejects_empty_string(self) -> None:
        """Bug #6575: Todo constructor should reject empty strings."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only(self) -> None:
        """Bug #6575: Todo constructor should reject whitespace-only strings."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n")

    def test_constructor_strips_whitespace_and_accepts_valid_text(self) -> None:
        """Bug #6575: Todo constructor should strip whitespace from valid text."""
        todo = Todo(id=1, text="  valid task  ")
        assert todo.text == "valid task"

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo constructor should accept valid non-empty text."""
        todo = Todo(id=1, text="buy milk")
        assert todo.text == "buy milk"


class TestTodoFromDictEmptyTextValidation:
    """Tests for Todo.from_dict() text validation (Issue #6575)."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Bug #6575: Todo.from_dict() should reject empty strings."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only(self) -> None:
        """Bug #6575: Todo.from_dict() should reject whitespace-only strings."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\n"})

    def test_from_dict_strips_whitespace_and_accepts_valid_text(self) -> None:
        """Bug #6575: Todo.from_dict() should strip whitespace from valid text."""
        todo = Todo.from_dict({"id": 1, "text": "  valid task  "})
        assert todo.text == "valid task"

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict() should accept valid non-empty text."""
        todo = Todo.from_dict({"id": 1, "text": "buy milk"})
        assert todo.text == "buy milk"


class TestTodoRenameEmptyTextValidation:
    """Tests for Todo.rename() text validation (already implemented in Bug #2085)."""

    def test_rename_rejects_empty_string(self) -> None:
        """Todo.rename() should reject empty strings (Bug #2085)."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("")

    def test_rename_rejects_whitespace_only(self) -> None:
        """Todo.rename() should reject whitespace-only strings (Bug #2085)."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")

        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("\t\n")

    def test_rename_strips_whitespace_and_accepts_valid_text(self) -> None:
        """Todo.rename() should strip whitespace from valid text."""
        todo = Todo(id=1, text="original")
        todo.rename("  new task  ")
        assert todo.text == "new task"
