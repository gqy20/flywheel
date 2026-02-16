"""Tests for issue #3677: Todo constructor and from_dict text validation consistency.

Bug: Todo constructor and from_dict allow empty/whitespace text but rename() rejects it,
creating data inconsistency. This test suite ensures validation is consistent across
all entry points.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorTextValidation:
    """Tests for Todo constructor text validation (issue #3677)."""

    def test_constructor_rejects_empty_text(self) -> None:
        """Bug #3677: Todo constructor should reject empty text like rename()."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_constructor_rejects_whitespace_only_text(self) -> None:
        """Bug #3677: Todo constructor should reject whitespace-only text like rename()."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_constructor_rejects_tabs_and_newlines_only(self) -> None:
        """Bug #3677: Todo constructor should reject whitespace including tabs/newlines."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\n  ")

    def test_constructor_strips_and_accepts_padded_text(self) -> None:
        """Bug #3677: Todo constructor should strip whitespace like rename()."""
        todo = Todo(id=1, text="  valid text  ")
        assert todo.text == "valid text"

    def test_constructor_accepts_valid_text(self) -> None:
        """Verify Todo constructor still works with valid text."""
        todo = Todo(id=1, text="valid todo text")
        assert todo.text == "valid todo text"


class TestTodoFromDictTextValidation:
    """Tests for Todo.from_dict text validation (issue #3677)."""

    def test_from_dict_rejects_empty_text(self) -> None:
        """Bug #3677: from_dict should reject empty text like rename()."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_text(self) -> None:
        """Bug #3677: from_dict should reject whitespace-only text like rename()."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_rejects_tabs_and_newlines_only(self) -> None:
        """Bug #3677: from_dict should reject whitespace including tabs/newlines."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\n  "})

    def test_from_dict_strips_and_accepts_padded_text(self) -> None:
        """Bug #3677: from_dict should strip whitespace like rename()."""
        todo = Todo.from_dict({"id": 1, "text": "  valid text  "})
        assert todo.text == "valid text"

    def test_from_dict_accepts_valid_text(self) -> None:
        """Verify from_dict still works with valid text."""
        todo = Todo.from_dict({"id": 1, "text": "valid todo text"})
        assert todo.text == "valid todo text"


class TestTextValidationConsistency:
    """Tests to ensure text validation is consistent across all entry points."""

    def test_validation_message_consistency(self) -> None:
        """Verify that constructor, from_dict, and rename use same error message."""
        expected_message = "Todo text cannot be empty"

        # Constructor
        with pytest.raises(ValueError, match=expected_message):
            Todo(id=1, text="")

        # from_dict
        with pytest.raises(ValueError, match=expected_message):
            Todo.from_dict({"id": 1, "text": ""})

        # rename
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match=expected_message):
            todo.rename("")

    def test_stripping_behavior_consistency(self) -> None:
        """Verify whitespace stripping is consistent across all entry points."""
        padded_text = "  hello world  "
        stripped_text = "hello world"

        # Constructor
        todo1 = Todo(id=1, text=padded_text)
        assert todo1.text == stripped_text

        # from_dict
        todo2 = Todo.from_dict({"id": 2, "text": padded_text})
        assert todo2.text == stripped_text

        # rename
        todo3 = Todo(id=3, text="original")
        todo3.rename(padded_text)
        assert todo3.text == stripped_text
