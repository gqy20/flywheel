"""Tests for Todo.id validation (Issue #6644).

These tests verify that:
1. Todo.id rejects negative values
2. Todo.id rejects zero value
3. Todo.id accepts positive values
4. Validation applies both to direct construction and from_dict()
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoIdValidationDirect:
    """Tests for Todo.id validation via direct construction."""

    def test_todo_rejects_negative_id(self) -> None:
        """Bug #6644: Todo should reject negative id values."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo(id=-1, text="test todo")

    def test_todo_rejects_zero_id(self) -> None:
        """Bug #6644: Todo should reject zero id value."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo(id=0, text="test todo")

    def test_todo_accepts_positive_id(self) -> None:
        """Todo should accept positive id values."""
        todo = Todo(id=1, text="test todo")
        assert todo.id == 1

        todo2 = Todo(id=42, text="another todo")
        assert todo2.id == 42


class TestTodoIdValidationFromDict:
    """Tests for Todo.id validation via from_dict()."""

    def test_from_dict_rejects_negative_id(self) -> None:
        """Bug #6644: from_dict should reject negative id values."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo.from_dict({"id": -1, "text": "test todo"})

    def test_from_dict_rejects_zero_id(self) -> None:
        """Bug #6644: from_dict should reject zero id value."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo.from_dict({"id": 0, "text": "test todo"})

    def test_from_dict_accepts_positive_id(self) -> None:
        """from_dict should accept positive id values."""
        todo = Todo.from_dict({"id": 1, "text": "test todo"})
        assert todo.id == 1

        todo2 = Todo.from_dict({"id": 100, "text": "another todo"})
        assert todo2.id == 100
