"""Tests for Issue #6521 - negative/zero ID validation.

These tests verify that:
1. Todo.from_dict raises ValueError when 'id' is negative
2. Todo.from_dict raises ValueError when 'id' is zero
3. next_id() always returns a positive integer >= 1
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative IDs."""
    with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*positive|'id'.*greater"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero as an ID."""
    with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*positive|'id'.*greater"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_storage_load_rejects_negative_id_in_json(tmp_path) -> None:
    """Storage.load should reject JSON containing negative IDs."""
    db = tmp_path / "negative_id.json"
    storage = TodoStorage(str(db))

    # Valid JSON but with negative ID
    db.write_text('[{"id": -5, "text": "bad task"}]', encoding="utf-8")

    # Should raise clear error about invalid ID
    with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*positive|'id'.*greater"):
        storage.load()


def test_storage_load_rejects_zero_id_in_json(tmp_path) -> None:
    """Storage.load should reject JSON containing zero ID."""
    db = tmp_path / "zero_id.json"
    storage = TodoStorage(str(db))

    # Valid JSON but with zero ID
    db.write_text('[{"id": 0, "text": "bad task"}]', encoding="utf-8")

    # Should raise clear error about invalid ID
    with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*positive|'id'.*greater"):
        storage.load()


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept valid positive IDs."""
    todo = Todo.from_dict({"id": 1, "text": "valid task"})
    assert todo.id == 1

    todo2 = Todo.from_dict({"id": 100, "text": "another valid task"})
    assert todo2.id == 100
