"""Tests for Todo text validation in constructor (Issue #7091).

These tests verify that:
1. Todo constructor rejects empty text
2. Todo constructor rejects whitespace-only text
3. Todo.from_dict rejects empty/whitespace text
4. Validation is consistent with rename() method
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorTextValidation:
    """Test that Todo constructor validates text field."""

    def test_constructor_rejects_empty_text(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_text(self) -> None:
        """Todo(id=1, text='   ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_tab_only_text(self) -> None:
        """Todo(id=1, text='\\t\\t') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_constructor_rejects_mixed_whitespace_text(self) -> None:
        """Todo(id=1, text='  \\t  ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t  ")

    def test_constructor_accepts_valid_text(self) -> None:
        """Todo with valid text should be created successfully."""
        todo = Todo(id=1, text="buy milk")
        assert todo.text == "buy milk"

    def test_constructor_strips_whitespace_from_valid_text(self) -> None:
        """Constructor should strip whitespace like rename() does."""
        todo = Todo(id=1, text="  buy milk  ")
        # Note: This test verifies behavior matches rename()
        # If we want to preserve whitespace, this test should change
        assert todo.text == "buy milk"


class TestTodoFromDictTextValidation:
    """Test that Todo.from_dict validates text field."""

    def test_from_dict_rejects_empty_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': '   '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict with valid text should work."""
        todo = Todo.from_dict({"id": 1, "text": "buy milk"})
        assert todo.text == "buy milk"


class TestTodoRenameConsistency:
    """Test that constructor validation matches rename() validation."""

    def test_validation_message_matches_rename(self) -> None:
        """Error message should be consistent with rename()."""
        # Get the error message from rename()
        with pytest.raises(ValueError) as exc_info:
            todo = Todo(id=1, text="valid")
            todo.rename("")

        rename_message = str(exc_info.value)

        # Constructor should raise the same message
        with pytest.raises(ValueError) as constructor_exc:
            Todo(id=1, text="")

        constructor_message = str(constructor_exc.value)

        assert rename_message == constructor_message

    def test_whitespace_handling_matches_rename(self) -> None:
        """Constructor should handle whitespace same as rename()."""
        # Create a valid todo
        todo = Todo(id=1, text="valid")
        # Rename strips whitespace
        todo.rename("  new text  ")
        assert todo.text == "new text"

        # Constructor should also strip
        todo2 = Todo(id=2, text="  new text  ")
        assert todo2.text == "new text"
