"""Tests for Todo positive ID validation (Issue #3707).

These tests verify that:
1. Todo rejects id=0 with ValueError
2. Todo rejects negative id with ValueError
3. Todo.from_dict rejects negative ID with ValueError
4. Valid positive IDs continue to work
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoPositiveIdValidation:
    """Tests for validating that Todo IDs must be positive integers."""

    def test_todo_rejects_zero_id(self) -> None:
        """Todo(id=0, text='test') should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo(id=0, text="test")
        assert "positive" in str(exc_info.value).lower()

    def test_todo_rejects_negative_id(self) -> None:
        """Todo(id=-1, text='test') should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo(id=-1, text="test")
        assert "positive" in str(exc_info.value).lower()

    def test_todo_rejects_negative_id_minus_five(self) -> None:
        """Todo should reject any negative ID."""
        with pytest.raises(ValueError) as exc_info:
            Todo(id=-5, text="another test")
        assert "positive" in str(exc_info.value).lower()

    def test_todo_accepts_positive_id_one(self) -> None:
        """Todo(id=1, text='test') should succeed."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1
        assert todo.text == "test"

    def test_todo_accepts_positive_id_large(self) -> None:
        """Todo should accept large positive IDs."""
        todo = Todo(id=999999, text="large id test")
        assert todo.id == 999999

    def test_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict with id=0 should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": 0, "text": "test"})
        assert "positive" in str(exc_info.value).lower()

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict with negative ID should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": -1, "text": "test"})
        assert "positive" in str(exc_info.value).lower()

    def test_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict with positive ID should succeed."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.id == 1

    def test_from_dict_rejects_string_negative_id(self) -> None:
        """Todo.from_dict should validate ID even when passed as string."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": "-10", "text": "test"})
        assert "positive" in str(exc_info.value).lower()
