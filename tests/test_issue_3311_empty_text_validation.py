"""Tests for Todo empty text validation (Issue #3311).

These tests verify that:
1. Todo constructor rejects empty text strings
2. Todo constructor rejects whitespace-only text strings
3. Todo.from_dict rejects empty text strings
4. Todo.from_dict rejects whitespace-only text strings

This ensures consistency with the rename() method which already validates this.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorEmptyTextValidation:
    """Tests for Todo constructor rejecting empty/whitespace text."""

    def test_todo_constructor_rejects_empty_string(self) -> None:
        """Todo(id=1, text="") should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="")

    def test_todo_constructor_rejects_whitespace_only(self) -> None:
        """Todo(id=1, text="   ") should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_constructor_rejects_tab_only(self) -> None:
        """Todo(id=1, text="\\t") should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="\t")

    def test_todo_constructor_rejects_newline_only(self) -> None:
        """Todo(id=1, text="\\n") should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="\n")

    def test_todo_constructor_rejects_mixed_whitespace(self) -> None:
        """Todo(id=1, text="  \\t\\n  ") should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="  \t\n  ")

    def test_todo_constructor_accepts_valid_text(self) -> None:
        """Todo(id=1, text="valid") should work normally."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_todo_constructor_strips_whitespace(self) -> None:
        """Todo should strip leading/trailing whitespace like rename()."""
        todo = Todo(id=1, text="  valid task  ")
        assert todo.text == "valid task"


class TestTodoFromDictEmptyTextValidation:
    """Tests for Todo.from_dict rejecting empty/whitespace text."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """from_dict({"id": 1, "text": ""}) should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only(self) -> None:
        """from_dict({"id": 1, "text": "   "}) should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tab_only(self) -> None:
        """from_dict({"id": 1, "text": "\\t"}) should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t"})

    def test_from_dict_rejects_newline_only(self) -> None:
        """from_dict({"id": 1, "text": "\\n"}) should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\n"})

    def test_from_dict_accepts_valid_text(self) -> None:
        """from_dict({"id": 1, "text": "valid"}) should work normally."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.text == "valid"

    def test_from_dict_strips_whitespace(self) -> None:
        """from_dict should strip leading/trailing whitespace."""
        todo = Todo.from_dict({"id": 1, "text": "  valid task  "})
        assert todo.text == "valid task"


class TestTodoRenameConsistency:
    """Tests to verify consistency between constructor and rename()."""

    def test_rename_rejects_empty_string(self) -> None:
        """rename("") should raise ValueError (existing behavior)."""
        todo = Todo(id=1, text="initial")
        with pytest.raises(ValueError, match="cannot be empty"):
            todo.rename("")

    def test_rename_rejects_whitespace_only(self) -> None:
        """rename("   ") should raise ValueError (existing behavior)."""
        todo = Todo(id=1, text="initial")
        with pytest.raises(ValueError, match="cannot be empty"):
            todo.rename("   ")

    def test_rename_accepts_valid_text(self) -> None:
        """rename("valid") should work (existing behavior)."""
        todo = Todo(id=1, text="initial")
        todo.rename("new text")
        assert todo.text == "new text"
