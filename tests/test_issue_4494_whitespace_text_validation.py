"""Tests for whitespace-only text validation in Todo (Issue #4494).

These tests verify that:
1. Todo constructor rejects whitespace-only text
2. Todo.from_dict rejects whitespace-only text
3. Valid text with surrounding whitespace is preserved
4. rename() already rejects whitespace-only text (existing behavior)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestWhitespaceOnlyTextValidation:
    """Test that whitespace-only text is rejected consistently."""

    def test_direct_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_direct_constructor_rejects_tabs_only(self) -> None:
        """Todo(id=1, text='\\t\\t') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_direct_constructor_rejects_mixed_whitespace(self) -> None:
        """Todo(id=1, text='  \\t  \\n  ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t  \n  ")

    def test_direct_constructor_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tabs_only(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '\\t\\t'}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\t"})

    def test_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_valid_text_works_normally(self) -> None:
        """Todo(id=1, text='valid') should work normally."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_valid_text_with_leading_trailing_whitespace_preserved(self) -> None:
        """Text with leading/trailing whitespace should be preserved as-is.

        Note: The rename() method strips text, but the constructor preserves it.
        This test documents current behavior - the constructor does NOT strip.
        """
        # The fix only validates that text.strip() is non-empty,
        # it does NOT modify the original text
        todo = Todo(id=1, text="  valid text  ")
        # Text is preserved as-is (not stripped by constructor)
        assert todo.text == "  valid text  "

    def test_from_dict_valid_text_works(self) -> None:
        """Todo.from_dict with valid text should work normally."""
        todo = Todo.from_dict({"id": 1, "text": "buy milk"})
        assert todo.text == "buy milk"

    def test_rename_still_rejects_whitespace_only(self) -> None:
        """rename() should continue to reject whitespace-only text."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")
