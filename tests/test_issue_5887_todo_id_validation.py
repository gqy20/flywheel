"""Tests for Todo id validation (issue #5887).

Bug: Todo id field does not validate for positive integers, allowing
negative ids and zero id, which can cause storage and query issues.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdValidation:
    """Tests for Todo id validation ensuring id must be a positive integer."""

    def test_todo_constructor_rejects_zero_id(self) -> None:
        """Bug #5887: Todo(id=0, ...) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo(id=0, text="test")

    def test_todo_constructor_rejects_negative_id(self) -> None:
        """Bug #5887: Todo(id=-1, ...) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo(id=-1, text="test")

    def test_todo_constructor_accepts_positive_id(self) -> None:
        """Verify positive ids are still accepted."""
        todo = Todo(id=1, text="valid")
        assert todo.id == 1

        todo = Todo(id=100, text="also valid")
        assert todo.id == 100

    def test_todo_from_dict_rejects_zero_id(self) -> None:
        """Bug #5887: Todo.from_dict with id=0 should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Bug #5887: Todo.from_dict with id=-1 should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo.from_dict({"id": -1, "text": "test"})

    def test_todo_from_dict_accepts_positive_id(self) -> None:
        """Verify positive ids are still accepted via from_dict."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.id == 1

        todo = Todo.from_dict({"id": 50, "text": "also valid", "done": True})
        assert todo.id == 50
