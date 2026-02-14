"""Tests for issue #3158: Todo constructor and from_dict text validation.

This test file ensures that Todo's text field is validated consistently:
- Direct construction with empty/whitespace-only text should raise ValueError
- from_dict with empty/whitespace-only text should raise ValueError
- The behavior should match rename() validation
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorTextValidation:
    """Test that Todo constructor validates text field."""

    def test_constructor_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_string(self) -> None:
        """Todo(id=1, text=' ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text=" ")

    def test_constructor_rejects_tabs_and_newlines(self) -> None:
        """Todo(id=1, text='\\t\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n")

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo with valid text should be created successfully."""
        todo = Todo(id=1, text="buy milk")
        assert todo.text == "buy milk"

    def test_constructor_strips_whitespace(self) -> None:
        """Valid text with leading/trailing whitespace should be stripped."""
        todo = Todo(id=1, text="  buy milk  ")
        assert todo.text == "buy milk"


class TestTodoFromDictTextValidation:
    """Test that Todo.from_dict validates text field."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict with empty text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_string(self) -> None:
        """Todo.from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": " "})

    def test_from_dict_rejects_tabs_and_newlines(self) -> None:
        """Todo.from_dict with tabs/newlines text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\n"})

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict with valid text should work."""
        todo = Todo.from_dict({"id": 1, "text": "buy milk"})
        assert todo.text == "buy milk"

    def test_from_dict_strips_whitespace(self) -> None:
        """Valid text with leading/trailing whitespace should be stripped."""
        todo = Todo.from_dict({"id": 1, "text": "  buy milk  "})
        assert todo.text == "buy milk"


class TestRenameConsistency:
    """Ensure rename() tests continue to pass (regression check)."""

    def test_rename_rejects_empty_string(self) -> None:
        """Existing behavior: rename() rejects empty string."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("")

    def test_rename_rejects_whitespace_only(self) -> None:
        """Existing behavior: rename() rejects whitespace-only string."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename(" ")
