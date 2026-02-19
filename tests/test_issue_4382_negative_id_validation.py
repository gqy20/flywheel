"""Tests for Todo negative ID validation (Issue #4382).

These tests verify that:
1. Todo constructor rejects negative IDs
2. Todo.from_dict rejects negative IDs
3. Todo accepts id=0 as a valid edge case
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestNegativeIdValidation:
    """Tests for rejecting negative IDs in Todo."""

    def test_todo_constructor_rejects_negative_id(self) -> None:
        """Todo(id=-1, text='test') should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo(id=-1, text="test")
        assert "non-negative" in str(exc_info.value).lower()

    def test_todo_constructor_rejects_negative_id_minus_five(self) -> None:
        """Todo constructor should reject any negative ID."""
        with pytest.raises(ValueError) as exc_info:
            Todo(id=-5, text="another test")
        assert "non-negative" in str(exc_info.value).lower()

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict({'id': -1, 'text': 'test'}) should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": -1, "text": "test"})
        assert "non-negative" in str(exc_info.value).lower()

    def test_todo_from_dict_rejects_negative_id_minus_ten(self) -> None:
        """Todo.from_dict should reject any negative ID."""
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({"id": -10, "text": "test"})
        assert "non-negative" in str(exc_info.value).lower()

    def test_todo_accepts_zero_id(self) -> None:
        """Todo(id=0, text='test') should be accepted as edge case."""
        todo = Todo(id=0, text="test")
        assert todo.id == 0
        assert todo.text == "test"

    def test_todo_from_dict_accepts_zero_id(self) -> None:
        """Todo.from_dict should accept id=0."""
        todo = Todo.from_dict({"id": 0, "text": "test"})
        assert todo.id == 0

    def test_todo_positive_id_still_works(self) -> None:
        """Existing tests with positive IDs should continue to work."""
        todo = Todo(id=1, text="positive id")
        assert todo.id == 1

    def test_todo_from_dict_positive_id_still_works(self) -> None:
        """Todo.from_dict should accept positive IDs."""
        todo = Todo.from_dict({"id": 42, "text": "positive id"})
        assert todo.id == 42
