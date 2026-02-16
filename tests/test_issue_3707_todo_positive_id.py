"""Tests for issue #3707: Todo should reject non-positive ID values."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoPositiveIdValidation:
    """Regression tests for issue #3707: Todo must have positive ID."""

    def test_todo_rejects_id_zero(self) -> None:
        """Todo(id=0, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            Todo(id=0, text="test")

    def test_todo_rejects_negative_id(self) -> None:
        """Todo(id=-1, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            Todo(id=-1, text="test")

    def test_todo_accepts_positive_id(self) -> None:
        """Valid positive IDs should continue to work."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1
        assert todo.text == "test"

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict({'id': -1, ...}) should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            Todo.from_dict({"id": -1, "text": "test"})

    def test_from_dict_rejects_id_zero(self) -> None:
        """Todo.from_dict({'id': 0, ...}) should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_from_dict_accepts_positive_id(self) -> None:
        """Valid positive IDs via from_dict should work."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.id == 1
        assert todo.text == "test"
