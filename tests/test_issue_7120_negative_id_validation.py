"""Tests for issue #7120: Todo constructor/from_dict validates non-negative id.

Bug: Todo constructor and from_dict accept negative id values without validation.
Fix: Add validation to reject negative ids with clear error message.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoNegativeIdValidation:
    """Test that Todo rejects negative id values."""

    def test_constructor_rejects_negative_id(self) -> None:
        """Todo(id=-1, text='test') should raise ValueError."""
        with pytest.raises(ValueError, match="id must be non-negative"):
            Todo(id=-1, text="test")

    def test_constructor_accepts_zero_id(self) -> None:
        """Todo(id=0, text='test') should succeed (0 is valid)."""
        todo = Todo(id=0, text="test")
        assert todo.id == 0
        assert todo.text == "test"

    def test_constructor_accepts_positive_id(self) -> None:
        """Todo with positive id should continue to work."""
        todo = Todo(id=42, text="positive test")
        assert todo.id == 42

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict({'id': -5, 'text': 'test'}) should raise ValueError."""
        with pytest.raises(ValueError, match="id must be non-negative"):
            Todo.from_dict({"id": -5, "text": "test"})

    def test_from_dict_accepts_zero_id(self) -> None:
        """Todo.from_dict with id=0 should succeed."""
        todo = Todo.from_dict({"id": 0, "text": "test"})
        assert todo.id == 0

    def test_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict with positive id should continue to work."""
        todo = Todo.from_dict({"id": 100, "text": "test"})
        assert todo.id == 100
