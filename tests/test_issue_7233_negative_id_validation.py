"""Tests for Todo negative ID validation (Issue #7233).

These tests verify that:
1. Todo constructor rejects negative IDs
2. Todo.from_dict rejects negative IDs
3. Todo accepts zero as a valid ID (documented behavior)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestNegativeIdValidation:
    """Tests for validating that IDs cannot be negative."""

    def test_constructor_rejects_negative_id(self) -> None:
        """Todo(id=-1, text='test') should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*non-negative"):
            Todo(id=-1, text="test")

    def test_constructor_rejects_large_negative_id(self) -> None:
        """Todo(id=-999, text='test') should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*non-negative"):
            Todo(id=-999, text="test")

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict({'id': -1, 'text': 'test'}) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*non-negative"):
            Todo.from_dict({"id": -1, "text": "test"})

    def test_from_dict_rejects_large_negative_id(self) -> None:
        """Todo.from_dict({'id': -999, 'text': 'test'}) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*non-negative"):
            Todo.from_dict({"id": -999, "text": "test"})

    def test_constructor_accepts_zero_id(self) -> None:
        """Todo(id=0, text='test') should be accepted (id >= 0)."""
        todo = Todo(id=0, text="test")
        assert todo.id == 0

    def test_from_dict_accepts_zero_id(self) -> None:
        """Todo.from_dict with id=0 should be accepted (id >= 0)."""
        todo = Todo.from_dict({"id": 0, "text": "test"})
        assert todo.id == 0

    def test_constructor_accepts_positive_id(self) -> None:
        """Todo(id=1, text='test') should be accepted."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1

    def test_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict with positive id should be accepted."""
        todo = Todo.from_dict({"id": 42, "text": "test"})
        assert todo.id == 42
