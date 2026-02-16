"""Tests for Todo text validation consistency (Issue #3677).

These tests verify that text validation is consistent across:
1. Todo constructor (__post_init__)
2. Todo.from_dict() class method
3. Todo.rename() method

All entry points should strip whitespace and reject empty text.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorTextValidation:
    """Tests for Todo constructor text validation."""

    def test_constructor_rejects_empty_text(self) -> None:
        """Todo constructor should reject empty text string."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo constructor should reject whitespace-only text."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_tab_newline_whitespace(self) -> None:
        """Todo constructor should reject text with only tabs and newlines."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="\t\n  ")

    def test_constructor_strips_whitespace_from_valid_text(self) -> None:
        """Todo constructor should strip leading/trailing whitespace from valid text."""
        todo = Todo(id=1, text="  valid task  ")
        assert todo.text == "valid task"


class TestTodoFromDictTextValidation:
    """Tests for Todo.from_dict() text validation."""

    def test_from_dict_rejects_empty_text(self) -> None:
        """Todo.from_dict() should reject empty text string."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict() should reject whitespace-only text."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tab_newline_whitespace(self) -> None:
        """Todo.from_dict() should reject text with only tabs and newlines."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\n  "})

    def test_from_dict_strips_whitespace_from_valid_text(self) -> None:
        """Todo.from_dict() should strip leading/trailing whitespace from valid text."""
        todo = Todo.from_dict({"id": 1, "text": "  valid task  "})
        assert todo.text == "valid task"


class TestTodoRenameTextValidation:
    """Tests for Todo.rename() text validation (existing behavior)."""

    def test_rename_rejects_empty_text(self) -> None:
        """Todo.rename() should reject empty text string."""
        todo = Todo(id=1, text="existing task")
        with pytest.raises(ValueError, match="cannot be empty"):
            todo.rename("")

    def test_rename_rejects_whitespace_only_text(self) -> None:
        """Todo.rename() should reject whitespace-only text."""
        todo = Todo(id=1, text="existing task")
        with pytest.raises(ValueError, match="cannot be empty"):
            todo.rename("   ")

    def test_rename_strips_whitespace_from_valid_text(self) -> None:
        """Todo.rename() should strip leading/trailing whitespace from valid text."""
        todo = Todo(id=1, text="existing task")
        todo.rename("  new task  ")
        assert todo.text == "new task"


class TestTextValidationConsistency:
    """Tests to verify consistent behavior across all entry points."""

    def test_all_entry_points_use_same_error_message(self) -> None:
        """All validation entry points should use the same error message."""
        # Constructor error message
        with pytest.raises(ValueError) as exc_info:
            Todo(id=1, text="")
        constructor_msg = str(exc_info.value)

        # from_dict error message
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": 1, "text": ""})
        from_dict_msg = str(exc_info.value)

        # rename error message
        todo = Todo(id=1, text="task")
        with pytest.raises(ValueError) as exc_info:
            todo.rename("")
        rename_msg = str(exc_info.value)

        # All should mention "empty"
        assert "empty" in constructor_msg.lower()
        assert "empty" in from_dict_msg.lower()
        assert "empty" in rename_msg.lower()
