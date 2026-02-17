"""Regression test for issue #3978.

Todo constructor accepts empty or whitespace-only text, but rename() rejects them.
This test ensures validation is consistent between constructor, rename(), and from_dict().
"""

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Tests for consistent empty/whitespace text validation."""

    def test_constructor_rejects_empty_text(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_strips_whitespace_and_accepts_non_empty(self) -> None:
        """Todo(id=1, text='  valid  ') should succeed and strip whitespace."""
        todo = Todo(id=1, text="  valid  ")
        assert todo.text == "valid"

    def test_from_dict_rejects_empty_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_strips_whitespace_and_accepts_non_empty(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '  valid  '}) should strip whitespace."""
        todo = Todo.from_dict({"id": 1, "text": "  valid  "})
        assert todo.text == "valid"

    def test_rename_rejects_empty_text(self) -> None:
        """rename('') should raise ValueError (existing behavior)."""
        todo = Todo(id=1, text="valid")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("")

    def test_rename_rejects_whitespace_only_text(self) -> None:
        """rename('   ') should raise ValueError (existing behavior)."""
        todo = Todo(id=1, text="valid")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")

    def test_rename_strips_whitespace(self) -> None:
        """rename('  new  ') should strip whitespace (existing behavior)."""
        todo = Todo(id=1, text="old")
        todo.rename("  new  ")
        assert todo.text == "new"
