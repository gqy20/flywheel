"""Tests for Todo id validation (Issue #3847).

These tests verify that:
1. Todo.__init__ rejects id <= 0 (zero and negative integers)
2. Todo.from_dict rejects id <= 0
3. Valid positive integers are accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoInitIdValidation:
    """Tests for Todo.__init__ id validation."""

    def test_init_rejects_zero_id(self) -> None:
        """Todo(id=0, ...) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo(id=0, text="test")

    def test_init_rejects_negative_id(self) -> None:
        """Todo(id=-1, ...) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo(id=-1, text="test")

    def test_init_rejects_large_negative_id(self) -> None:
        """Todo(id=-100, ...) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo(id=-100, text="test")

    def test_init_accepts_positive_id(self) -> None:
        """Todo(id=1, ...) should work normally."""
        todo = Todo(id=1, text="valid")
        assert todo.id == 1
        assert todo.text == "valid"

    def test_init_accepts_large_positive_id(self) -> None:
        """Todo with large positive id should work."""
        todo = Todo(id=999999, text="valid")
        assert todo.id == 999999


class TestTodoFromDictIdValidation:
    """Tests for Todo.from_dict id validation."""

    def test_from_dict_rejects_zero_id(self) -> None:
        """from_dict with id=0 should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo.from_dict({"id": 0, "text": "test"})

    def test_from_dict_rejects_negative_id(self) -> None:
        """from_dict with id=-5 should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo.from_dict({"id": -5, "text": "test"})

    def test_from_dict_rejects_string_zero_id(self) -> None:
        """from_dict with id='0' (string) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo.from_dict({"id": "0", "text": "test"})

    def test_from_dict_rejects_string_negative_id(self) -> None:
        """from_dict with id='-10' (string) should raise ValueError."""
        with pytest.raises(ValueError, match=r"id.*must be.*positive"):
            Todo.from_dict({"id": "-10", "text": "test"})

    def test_from_dict_accepts_positive_id(self) -> None:
        """from_dict with positive id should work."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.id == 1

    def test_from_dict_accepts_string_positive_id(self) -> None:
        """from_dict with string positive id should work."""
        todo = Todo.from_dict({"id": "42", "text": "valid"})
        assert todo.id == 42
