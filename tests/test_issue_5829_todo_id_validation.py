"""Tests for issue #5829: Todo ID validation.

Bug: Todo accepts negative and zero IDs without validation, leading to
inconsistent behavior in next_id calculation.

Root cause: The 'id' field in Todo dataclass has no validation constraints.
When all IDs are negative, storage.next_id() returns max() of negative values
plus 1, which could be 0 or negative, leading to inconsistent behavior.

Fix: Add validation in __post_init__ and from_dict to ensure id > 0.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Test suite for Todo ID validation (issue #5829)."""

    def test_todo_rejects_zero_id(self) -> None:
        """Bug #5829: Todo(id=0, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="'id' must be a positive integer"):
            Todo(id=0, text="test")

    def test_todo_rejects_negative_id(self) -> None:
        """Bug #5829: Todo(id=-1, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="'id' must be a positive integer"):
            Todo(id=-1, text="test")

    def test_todo_rejects_large_negative_id(self) -> None:
        """Bug #5829: Todo with any negative ID should raise ValueError."""
        with pytest.raises(ValueError, match="'id' must be a positive integer"):
            Todo(id=-100, text="test")

    def test_todo_accepts_positive_id(self) -> None:
        """Valid Todo with positive ID should work normally."""
        todo = Todo(id=1, text="valid todo")
        assert todo.id == 1
        assert todo.text == "valid todo"

    def test_from_dict_rejects_zero_id(self) -> None:
        """Bug #5829: Todo.from_dict with id=0 should raise ValueError."""
        with pytest.raises(ValueError, match="'id' must be a positive integer"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_from_dict_rejects_negative_id(self) -> None:
        """Bug #5829: Todo.from_dict with negative ID should raise ValueError."""
        with pytest.raises(ValueError, match="'id' must be a positive integer"):
            Todo.from_dict({"id": -5, "text": "test"})

    def test_from_dict_accepts_positive_id(self) -> None:
        """Valid Todo.from_dict with positive ID should work normally."""
        todo = Todo.from_dict({"id": 42, "text": "valid todo"})
        assert todo.id == 42
        assert todo.text == "valid todo"
