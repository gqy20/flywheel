"""Regression tests for Issue #5887: Todo id field validation.

This test file ensures that the Todo id field is validated to be a positive integer.
- Zero and negative ids should raise ValueError
- Positive integers should be accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Tests for validating that Todo id must be a positive integer."""

    def test_todo_constructor_rejects_zero_id(self) -> None:
        """Todo(id=0, text='test') should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*positive|id.*greater.*0|invalid.*id"):
            Todo(id=0, text="test")

    def test_todo_constructor_rejects_negative_id(self) -> None:
        """Todo(id=-1, text='test') should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*positive|id.*greater.*0|invalid.*id"):
            Todo(id=-1, text="test")

    def test_todo_constructor_accepts_positive_id(self) -> None:
        """Valid positive integer id should be accepted."""
        todo = Todo(id=1, text="test")
        assert todo.id == 1

        todo2 = Todo(id=100, text="another test")
        assert todo2.id == 100

    def test_todo_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict({'id': 0, 'text': 'test'}) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*positive|id.*greater.*0|invalid.*id"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict({'id': -1, 'text': 'test'}) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*positive|id.*greater.*0|invalid.*id"):
            Todo.from_dict({"id": -1, "text": "test"})

    def test_todo_from_dict_accepts_positive_id(self) -> None:
        """Valid positive integer id should be accepted in from_dict."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.id == 1

        todo2 = Todo.from_dict({"id": 999, "text": "another test"})
        assert todo2.id == 999
