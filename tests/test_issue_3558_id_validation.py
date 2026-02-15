"""Tests for Issue #3558 - ID validation in from_dict and next_id.

Bug: from_dict accepts negative ID values without validation,
and next_id can return 0 when all existing IDs are negative.

Acceptance Criteria:
- Todo.from_dict({'id': -1, 'text': 'x'}) should raise ValueError
- Todo.from_dict({'id': 0, 'text': 'x'}) should raise ValueError
- Todo.from_dict({'id': 1, 'text': 'x'}) should succeed
- next_id([Todo(id=-1, text='a')]) should return 1, not 0
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestTodoFromDictIdValidation:
    """Tests for Todo.from_dict ID validation (Issue #3558)."""

    def test_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict should reject negative ID values."""
        with pytest.raises(ValueError, match=r"positive|invalid.*'id'|'id'.*>= 1"):
            Todo.from_dict({"id": -1, "text": "task"})

    def test_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict should reject zero ID value."""
        with pytest.raises(ValueError, match=r"positive|invalid.*'id'|'id'.*>= 1"):
            Todo.from_dict({"id": 0, "text": "task"})

    def test_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict should accept positive ID values."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.id == 1

        todo2 = Todo.from_dict({"id": 42, "text": "another task"})
        assert todo2.id == 42


class TestStorageNextIdNegativeHandling:
    """Tests for storage.next_id with negative IDs (Issue #3558)."""

    def test_next_id_returns_1_when_all_ids_are_negative(self) -> None:
        """next_id should return 1 when all existing IDs are negative."""
        storage = TodoStorage()
        todos = [Todo(id=-1, text="negative"), Todo(id=-5, text="also negative")]
        assert storage.next_id(todos) == 1

    def test_next_id_returns_1_when_empty(self) -> None:
        """next_id should return 1 when there are no todos."""
        storage = TodoStorage()
        assert storage.next_id([]) == 1

    def test_next_id_ignores_negative_ids(self) -> None:
        """next_id should ignore negative IDs when finding max."""
        storage = TodoStorage()
        # Mix of positive and negative IDs - should return max(positive) + 1
        todos = [Todo(id=-1, text="negative"), Todo(id=5, text="positive")]
        assert storage.next_id(todos) == 6
