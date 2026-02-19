"""Tests for negative/zero ID validation (Issue #4549).

These tests verify that:
1. Todo.from_dict rejects negative IDs
2. Todo.from_dict rejects zero ID
3. TodoStorage.next_id returns positive integers even with edge cases
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestTodoFromDictNegativeIdValidation:
    """Tests for Todo.from_dict negative and zero ID validation."""

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict should reject negative IDs."""
        with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*positive|'id'.*greater.*0"):
            Todo.from_dict({"id": -1, "text": "task"})

    def test_from_dict_rejects_negative_id_large(self) -> None:
        """Todo.from_dict should reject large negative IDs."""
        with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*positive|'id'.*greater.*0"):
            Todo.from_dict({"id": -999999, "text": "task"})

    def test_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict should reject zero ID."""
        with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*positive|'id'.*greater.*0"):
            Todo.from_dict({"id": 0, "text": "task"})

    def test_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict should accept positive IDs."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.id == 1

        todo = Todo.from_dict({"id": 100, "text": "task"})
        assert todo.id == 100


class TestStorageNextIdEdgeCases:
    """Tests for TodoStorage.next_id edge case handling."""

    def test_next_id_returns_1_for_empty_list(self) -> None:
        """next_id should return 1 when todo list is empty."""
        storage = TodoStorage()
        assert storage.next_id([]) == 1

    def test_next_id_returns_correct_value_for_positive_ids(self) -> None:
        """next_id should return max_id + 1 for positive IDs."""
        storage = TodoStorage()
        todos = [Todo(id=5, text="a"), Todo(id=10, text="b")]
        assert storage.next_id(todos) == 11
