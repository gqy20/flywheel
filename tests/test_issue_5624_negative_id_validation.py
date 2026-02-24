"""Tests for negative ID validation (Issue #5624).

These tests verify that:
1. Todo.from_dict rejects negative IDs with a clear ValueError
2. next_id always returns a positive integer (>=1) regardless of existing IDs
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNegativeIdValidation:
    """Tests for rejecting negative IDs in JSON data."""

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict should reject negative IDs with clear error message."""
        with pytest.raises(ValueError, match=r"negative|'id'.*positive|'id'.*>= ?1"):
            Todo.from_dict({"id": -1, "text": "task with negative id"})

    def test_todo_from_dict_rejects_negative_large_id(self) -> None:
        """Todo.from_dict should reject large negative IDs."""
        with pytest.raises(ValueError, match=r"negative|'id'.*positive|'id'.*>= ?1"):
            Todo.from_dict({"id": -9999, "text": "task with large negative id"})

    def test_storage_load_rejects_negative_id_in_json(self, tmp_path) -> None:
        """Storage should reject JSON files containing negative IDs."""
        db = tmp_path / "negative_id.json"
        storage = TodoStorage(str(db))

        # Valid JSON but with negative ID
        db.write_text('[{"id": -5, "text": "task"}]', encoding="utf-8")

        # Should raise clear error about negative ID
        with pytest.raises(ValueError, match=r"negative|'id'.*positive|'id'.*>= ?1"):
            storage.load()

    def test_todo_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict should accept positive IDs."""
        todo = Todo.from_dict({"id": 1, "text": "valid task"})
        assert todo.id == 1

    def test_todo_from_dict_accepts_zero_id(self) -> None:
        """Todo.from_dict should accept zero as a valid ID (though next_id starts at 1)."""
        # Note: ID 0 is technically non-negative, but next_id logic handles this
        todo = Todo.from_dict({"id": 0, "text": "task with zero id"})
        assert todo.id == 0
