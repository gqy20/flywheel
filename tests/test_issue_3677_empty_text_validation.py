"""Tests for issue #3677: Empty/whitespace text validation consistency.

This module tests that Todo constructor and from_dict reject empty/whitespace
text consistently with rename() behavior.
"""

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Test that Todo rejects empty/whitespace text in constructor."""

    def test_constructor_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_whitespace_with_tabs_and_newlines(self) -> None:
        """Todo(id=1, text='  \\t\\n  ') should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="  \t\n  ")


class TestTodoFromDictEmptyTextValidation:
    """Test that Todo.from_dict rejects empty/whitespace text."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_whitespace_with_tabs_and_newlines(self) -> None:
        """Todo.from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo.from_dict({"id": 1, "text": "  \t\n  "})


class TestTodoTextStripping:
    """Test that Todo strips whitespace from text like rename() does."""

    def test_constructor_strips_leading_trailing_whitespace(self) -> None:
        """Todo should strip whitespace from text like rename() does."""
        todo = Todo(id=1, text="  hello world  ")
        assert todo.text == "hello world"

    def test_from_dict_strips_leading_trailing_whitespace(self) -> None:
        """Todo.from_dict should strip whitespace from text like rename() does."""
        todo = Todo.from_dict({"id": 1, "text": "  hello world  "})
        assert todo.text == "hello world"


class TestTodoRenameConsistency:
    """Test that rename() behavior is consistent with constructor/from_dict."""

    def test_rename_rejects_empty_string(self) -> None:
        """rename('') should raise ValueError (existing behavior)."""
        todo = Todo(id=1, text="valid text")
        with pytest.raises(ValueError, match="cannot be empty"):
            todo.rename("")

    def test_rename_rejects_whitespace_only(self) -> None:
        """rename('   ') should raise ValueError (existing behavior)."""
        todo = Todo(id=1, text="valid text")
        with pytest.raises(ValueError, match="cannot be empty"):
            todo.rename("   ")

    def test_rename_strips_whitespace(self) -> None:
        """rename() should strip whitespace (existing behavior)."""
        todo = Todo(id=1, text="valid text")
        todo.rename("  new text  ")
        assert todo.text == "new text"
