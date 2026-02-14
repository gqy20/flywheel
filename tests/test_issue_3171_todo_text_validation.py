"""Regression tests for issue #3171: Todo constructor and from_dict text validation.

Bug: Todo constructor and from_dict accept empty or whitespace-only text without validation.
Fix: Add text validation in __post_init__ to reject empty/whitespace-only text.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorTextValidation:
    """Test that Todo constructor rejects empty and whitespace-only text."""

    def test_todo_constructor_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_constructor_rejects_whitespace_only(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError after strip."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_todo_constructor_rejects_whitespace_tabs_newlines(self) -> None:
        """Todo should reject various whitespace combinations."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n  ")

    def test_todo_constructor_accepts_valid_text(self) -> None:
        """Valid text should still work."""
        todo = Todo(id=1, text="valid todo")
        assert todo.text == "valid todo"

    def test_todo_constructor_preserves_text_as_is(self) -> None:
        """Constructor should preserve text as-is (not strip)."""
        todo = Todo(id=1, text="  valid  ")
        assert todo.text == "  valid  "


class TestTodoFromDictTextValidation:
    """Test that Todo.from_dict rejects empty and whitespace-only text."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only(self) -> None:
        """Todo.from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_whitespace_tabs_newlines(self) -> None:
        """Todo.from_dict should reject various whitespace combinations."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\n  "})

    def test_from_dict_preserves_valid_text_as_is(self) -> None:
        """from_dict should preserve valid text as-is (not strip)."""
        todo = Todo.from_dict({"id": 1, "text": "  valid  "})
        assert todo.text == "  valid  "

    def test_from_dict_accepts_valid_text(self) -> None:
        """Valid text should still work."""
        todo = Todo.from_dict({"id": 1, "text": "valid todo"})
        assert todo.text == "valid todo"
