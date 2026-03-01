"""Tests for negative ID validation (Issue #6521).

These tests verify that:
1. Todo.from_dict raises ValueError when 'id' is negative
2. Todo.from_dict raises ValueError when 'id' is zero
3. next_id() always returns a positive integer >= 1
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNegativeIdValidation:
    """Tests for Issue #6521 - validate 'id' field is positive."""

    def test_todo_from_dict_rejects_negative_id(self) -> None:
        """Todo.from_dict should reject negative IDs."""
        with pytest.raises(ValueError, match=r"'id'.*positive|'id'.*greater than 0|'id'.*> ?0"):
            Todo.from_dict({"id": -1, "text": "task"})

    def test_todo_from_dict_rejects_zero_id(self) -> None:
        """Todo.from_dict should reject zero as an ID."""
        with pytest.raises(ValueError, match=r"'id'.*positive|'id'.*greater than 0|'id'.*> ?0"):
            Todo.from_dict({"id": 0, "text": "task"})

    def test_todo_from_dict_accepts_positive_id(self) -> None:
        """Todo.from_dict should accept positive IDs."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.id == 1

        todo = Todo.from_dict({"id": 100, "text": "task"})
        assert todo.id == 100

    def test_storage_load_rejects_negative_id_in_json(self, tmp_path) -> None:
        """Storage.load should reject JSON with negative IDs."""
        db = tmp_path / "negative_id.json"
        storage = TodoStorage(str(db))

        # JSON with negative ID
        db.write_text('[{"id": -1, "text": "task"}]', encoding="utf-8")

        # Should raise clear error about invalid ID
        with pytest.raises(ValueError, match=r"'id'.*positive|'id'.*greater than 0|'id'.*> ?0"):
            storage.load()

    def test_storage_load_rejects_zero_id_in_json(self, tmp_path) -> None:
        """Storage.load should reject JSON with zero ID."""
        db = tmp_path / "zero_id.json"
        storage = TodoStorage(str(db))

        # JSON with zero ID
        db.write_text('[{"id": 0, "text": "task"}]', encoding="utf-8")

        # Should raise clear error about invalid ID
        with pytest.raises(ValueError, match=r"'id'.*positive|'id'.*greater than 0|'id'.*> ?0"):
            storage.load()

    def test_next_id_returns_positive_for_empty_list(self, tmp_path) -> None:
        """next_id() should return 1 for empty todo list."""
        storage = TodoStorage(str(tmp_path / "empty.json"))
        assert storage.next_id([]) == 1

    def test_next_id_returns_correct_value_for_positive_ids(self, tmp_path) -> None:
        """next_id() should return max(id) + 1 for positive IDs."""
        storage = TodoStorage(str(tmp_path / "normal.json"))
        todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=3, text="c")]
        assert storage.next_id(todos) == 6
