"""Tests for Todo negative id validation (Issue #7120).

These tests verify that:
1. Todo constructor rejects negative id values with ValueError
2. Todo.from_dict rejects negative id values with ValueError
3. Todo accepts id=0 (zero is valid)
4. Todo accepts positive id values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoNegativeIdValidation:
    """Test suite for Todo id validation."""

    def test_constructor_rejects_negative_id(self) -> None:
        """Todo(id=-1, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            Todo(id=-1, text="test")

    def test_constructor_rejects_large_negative_id(self) -> None:
        """Todo(id=-999, ...) should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            Todo(id=-999, text="test")

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict({'id': -5, ...}) should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            Todo.from_dict({"id": -5, "text": "test"})

    def test_from_dict_rejects_large_negative_id(self) -> None:
        """Todo.from_dict with large negative id should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            Todo.from_dict({"id": -100, "text": "test"})

    def test_constructor_accepts_zero_id(self) -> None:
        """Todo(id=0, ...) should succeed - zero is valid."""
        todo = Todo(id=0, text="test")
        assert todo.id == 0

    def test_constructor_accepts_positive_id(self) -> None:
        """Todo(id=1, ...) should succeed."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1

    def test_from_dict_accepts_zero_id(self) -> None:
        """Todo.from_dict with id=0 should succeed."""
        todo = Todo.from_dict({"id": 0, "text": "test"})
        assert todo.id == 0

    def test_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict with positive id should succeed."""
        todo = Todo.from_dict({"id": 42, "text": "test"})
        assert todo.id == 42
