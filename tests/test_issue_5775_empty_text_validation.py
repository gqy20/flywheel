"""Tests for Issue #5775: Inconsistent validation for empty/whitespace-only text.

These tests verify that Todo.from_dict() and Todo constructor reject empty
and whitespace-only text values, matching the behavior of Todo.rename().
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoFromDictRejectsEmptyText:
    """Tests for Todo.from_dict() rejecting empty/whitespace-only text."""

    def test_from_dict_rejects_empty_string_text(self) -> None:
        """Todo.from_dict should reject empty string for 'text' field."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict should reject whitespace-only string for 'text' field."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tabs_and_newlines_text(self) -> None:
        """Todo.from_dict should reject strings with only whitespace characters."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\n"})


class TestTodoConstructorRejectsEmptyText:
    """Tests for Todo constructor rejecting empty/whitespace-only text."""

    def test_constructor_rejects_empty_string_text(self) -> None:
        """Todo constructor should reject empty string for 'text' field."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo constructor should reject whitespace-only string for 'text' field."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_tabs_and_newlines_text(self) -> None:
        """Todo constructor should reject strings with only whitespace characters."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="\t\n")


class TestTodoAcceptsValidText:
    """Tests that valid text still works after validation changes."""

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict should still accept valid non-empty text."""
        todo = Todo.from_dict({"id": 1, "text": "valid task"})
        assert todo.text == "valid task"

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo constructor should still accept valid non-empty text."""
        todo = Todo(id=1, text="valid task")
        assert todo.text == "valid task"

    def test_roundtrip_to_dict_from_dict_works(self) -> None:
        """Roundtrip to_dict/from_dict should still work with valid text."""
        original = Todo(id=1, text="original task", done=True)
        data = original.to_dict()
        restored = Todo.from_dict(data)
        assert restored.id == original.id
        assert restored.text == original.text
        assert restored.done == original.done
