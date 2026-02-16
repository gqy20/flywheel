"""Tests for Todo id validation (Issue #3847).

These tests verify that:
1. Todo.__init__ rejects non-positive id values (0, negative)
2. Todo.from_dict rejects non-positive id values (0, negative)
3. Valid positive id values still work correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoInitIdValidation:
    """Tests for Todo.__init__ id validation."""

    def test_todo_init_rejects_zero_id(self) -> None:
        """Todo.__init__ should reject id=0."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo(id=0, text="test")

    def test_todo_init_rejects_negative_id(self) -> None:
        """Todo.__init__ should reject negative id values."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo(id=-1, text="test")

    def test_todo_init_rejects_large_negative_id(self) -> None:
        """Todo.__init__ should reject large negative id values."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo(id=-999, text="test")

    def test_todo_init_accepts_positive_id(self) -> None:
        """Todo.__init__ should accept valid positive id values."""
        todo = Todo(id=1, text="valid")
        assert todo.id == 1
        assert todo.text == "valid"

    def test_todo_init_accepts_large_positive_id(self) -> None:
        """Todo.__init__ should accept large positive id values."""
        todo = Todo(id=999999, text="valid large id")
        assert todo.id == 999999


class TestTodoFromDictIdValidation:
    """Tests for Todo.from_dict id validation."""

    def test_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict should reject id=0."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict should reject negative id values."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo.from_dict({"id": -1, "text": "test"})

    def test_from_dict_rejects_large_negative_id(self) -> None:
        """Todo.from_dict should reject large negative id values."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo.from_dict({"id": -5, "text": "test"})

    def test_from_dict_rejects_string_zero_id(self) -> None:
        """Todo.from_dict should reject string '0' as id."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo.from_dict({"id": "0", "text": "test"})

    def test_from_dict_rejects_string_negative_id(self) -> None:
        """Todo.from_dict should reject string negative numbers as id."""
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo.from_dict({"id": "-10", "text": "test"})

    def test_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict should accept valid positive id values."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.id == 1
        assert todo.text == "valid"

    def test_from_dict_accepts_string_positive_id(self) -> None:
        """Todo.from_dict should accept string positive numbers as id."""
        todo = Todo.from_dict({"id": "42", "text": "valid string id"})
        assert todo.id == 42
