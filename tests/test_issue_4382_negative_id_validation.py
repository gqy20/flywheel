"""Tests for Todo negative ID validation (Issue #4382).

These tests verify that:
1. Todo constructor rejects negative IDs with ValueError
2. Todo.from_dict rejects negative IDs with ValueError
3. Todo accepts id=0 as edge case (non-negative)
4. Todo accepts positive IDs as normal
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestNegativeIdValidation:
    """Tests for validating that Todo IDs must be non-negative."""

    def test_constructor_rejects_negative_id(self) -> None:
        """Todo(id=-1, text='test') should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo(id=-1, text="test")
        assert "non-negative" in str(exc_info.value).lower()

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict({'id': -1, 'text': 'test'}) should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": -1, "text": "test"})
        assert "non-negative" in str(exc_info.value).lower()

    def test_constructor_accepts_zero_id(self) -> None:
        """Todo(id=0, text='test') should be accepted (edge case)."""
        todo = Todo(id=0, text="test")
        assert todo.id == 0
        assert todo.text == "test"

    def test_from_dict_accepts_zero_id(self) -> None:
        """Todo.from_dict with id=0 should be accepted (edge case)."""
        todo = Todo.from_dict({"id": 0, "text": "test"})
        assert todo.id == 0
        assert todo.text == "test"

    def test_constructor_accepts_positive_id(self) -> None:
        """Todo with positive ID should work normally."""
        todo = Todo(id=1, text="positive id test")
        assert todo.id == 1
        assert todo.text == "positive id test"

    def test_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict with positive ID should work normally."""
        todo = Todo.from_dict({"id": 42, "text": "from dict test"})
        assert todo.id == 42
        assert todo.text == "from dict test"
