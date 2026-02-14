"""Regression tests for Issue #3158: Todo constructor and from_dict text validation.

This test file ensures that Todo constructor and from_dict reject empty/whitespace-only
text, matching the behavior of rename().
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorTextValidation:
    """Tests for Todo constructor text validation."""

    def test_constructor_empty_string_raises_value_error(self) -> None:
        """Todo(id=1, text='') should raise ValueError with message 'Todo text cannot be empty'."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_whitespace_only_raises_value_error(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError with message 'Todo text cannot be empty'."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_whitespace_with_tabs_raises_value_error(self) -> None:
        """Todo with tabs/whitespace only should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t \n")

    def test_constructor_valid_text_with_leading_trailing_whitespace_stripped(
        self,
    ) -> None:
        """Valid text with leading/trailing whitespace should be stripped."""
        todo = Todo(id=1, text="  Buy milk  ")
        assert todo.text == "Buy milk"

    def test_constructor_valid_text_unchanged(self) -> None:
        """Valid text without extra whitespace should be unchanged."""
        todo = Todo(id=1, text="Buy milk")
        assert todo.text == "Buy milk"


class TestTodoFromDictTextValidation:
    """Tests for Todo.from_dict text validation."""

    def test_from_dict_empty_text_raises_value_error(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_whitespace_only_raises_value_error(self) -> None:
        """Todo.from_dict with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_whitespace_with_tabs_raises_value_error(self) -> None:
        """Todo.from_dict with tabs/whitespace only should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t \n"})

    def test_from_dict_valid_text_with_whitespace_stripped(self) -> None:
        """Valid text with leading/trailing whitespace should be stripped via from_dict."""
        todo = Todo.from_dict({"id": 1, "text": "  Buy milk  "})
        assert todo.text == "Buy milk"

    def test_from_dict_valid_text_unchanged(self) -> None:
        """Valid text without extra whitespace should be unchanged via from_dict."""
        todo = Todo.from_dict({"id": 1, "text": "Buy milk"})
        assert todo.text == "Buy milk"


class TestRenameBehaviorConsistency:
    """Tests to ensure rename() behavior is consistent with constructor/from_dict."""

    def test_rename_empty_raises_same_error(self) -> None:
        """rename('') should raise same ValueError as constructor."""
        todo = Todo(id=1, text="Buy milk")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("")

    def test_rename_whitespace_raises_same_error(self) -> None:
        """rename('   ') should raise same ValueError as constructor."""
        todo = Todo(id=1, text="Buy milk")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")

    def test_rename_valid_text_with_whitespace_stripped(self) -> None:
        """rename with valid text should strip whitespace."""
        todo = Todo(id=1, text="Buy milk")
        todo.rename("  New task  ")
        assert todo.text == "New task"
