"""Regression tests for Issue #5887: Todo id field validation.

This test file ensures that Todo id field validates positive integers,
rejecting zero and negative id values.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Tests for Todo id field validation."""

    def test_todo_with_zero_id_raises_value_error(self) -> None:
        """Todo with id=0 should raise ValueError."""
        with pytest.raises(ValueError, match=r"id must be a positive integer"):
            Todo(id=0, text="test")

    def test_todo_with_negative_id_raises_value_error(self) -> None:
        """Todo with negative id should raise ValueError."""
        with pytest.raises(ValueError, match=r"id must be a positive integer"):
            Todo(id=-1, text="test")

    def test_todo_with_valid_positive_id_succeeds(self) -> None:
        """Todo with valid positive id should be created successfully."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1
        assert todo.text == "test"

    def test_todo_with_large_positive_id_succeeds(self) -> None:
        """Todo with large positive id should be created successfully."""
        todo = Todo(id=999999, text="test")
        assert todo.id == 999999


class TestTodoFromDictIdValidation:
    """Tests for Todo.from_dict id validation."""

    def test_from_dict_with_zero_id_raises_value_error(self) -> None:
        """Todo.from_dict with id=0 should raise ValueError."""
        with pytest.raises(ValueError, match=r"id must be a positive integer"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_from_dict_with_negative_id_raises_value_error(self) -> None:
        """Todo.from_dict with negative id should raise ValueError."""
        with pytest.raises(ValueError, match=r"id must be a positive integer"):
            Todo.from_dict({"id": -1, "text": "test"})

    def test_from_dict_with_valid_positive_id_succeeds(self) -> None:
        """Todo.from_dict with valid positive id should succeed."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.id == 1
        assert todo.text == "test"

    def test_from_dict_with_string_positive_id_succeeds(self) -> None:
        """Todo.from_dict with string positive id should succeed (converted to int)."""
        todo = Todo.from_dict({"id": "42", "text": "test"})
        assert todo.id == 42

    def test_from_dict_with_string_zero_id_raises_value_error(self) -> None:
        """Todo.from_dict with string '0' id should raise ValueError."""
        with pytest.raises(ValueError, match=r"id must be a positive integer"):
            Todo.from_dict({"id": "0", "text": "test"})

    def test_from_dict_with_string_negative_id_raises_value_error(self) -> None:
        """Todo.from_dict with string negative id should raise ValueError."""
        with pytest.raises(ValueError, match=r"id must be a positive integer"):
            Todo.from_dict({"id": "-5", "text": "test"})
