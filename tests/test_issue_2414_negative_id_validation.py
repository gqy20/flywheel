"""Tests for negative/zero ID validation (Issue #2414).

These tests verify that:
1. Todo.from_dict() rejects negative IDs
2. Todo.from_dict() rejects zero IDs
3. next_id() returns valid IDs (>= 1) in all cases
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative IDs."""
    with pytest.raises(ValueError, match=r"id.*must be positive|invalid.*'id'|'id'.*positive"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero IDs."""
    with pytest.raises(ValueError, match=r"id.*must be positive|invalid.*'id'|'id'.*positive"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_rejects_large_negative_id() -> None:
    """Todo.from_dict should reject large negative IDs."""
    with pytest.raises(ValueError, match=r"id.*must be positive|invalid.*'id'|'id'.*positive"):
        Todo.from_dict({"id": -999, "text": "task"})


def test_storage_load_rejects_json_with_negative_id(tmp_path) -> None:
    """Storage.load() should reject JSON containing negative IDs."""
    db = tmp_path / "negative_id.json"
    storage = TodoStorage(str(db))

    # Valid JSON with negative ID
    db.write_text('[{"id": -1, "text": "task"}]', encoding="utf-8")

    # Should raise ValueError about negative/zero ID
    with pytest.raises(ValueError, match=r"id.*must be positive|invalid.*'id'|'id'.*positive"):
        storage.load()


def test_storage_load_rejects_json_with_zero_id(tmp_path) -> None:
    """Storage.load() should reject JSON containing zero IDs."""
    db = tmp_path / "zero_id.json"
    storage = TodoStorage(str(db))

    # Valid JSON with zero ID
    db.write_text('[{"id": 0, "text": "task"}]', encoding="utf-8")

    # Should raise ValueError about negative/zero ID
    with pytest.raises(ValueError, match=r"id.*must be positive|invalid.*'id'|'id'.*positive"):
        storage.load()


def test_next_id_returns_at_least_one_for_empty_list() -> None:
    """next_id() should return 1 for empty todo list."""
    storage = TodoStorage()
    assert storage.next_id([]) == 1


def test_next_id_returns_max_plus_one_for_single_todo() -> None:
    """next_id() should return max(id) + 1 for single todo."""
    storage = TodoStorage()
    todo = Todo(id=5, text="task")
    assert storage.next_id([todo]) == 6


def test_next_id_returns_max_plus_one_for_multiple_todos() -> None:
    """next_id() should return max(id) + 1 for multiple todos."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="task1"), Todo(id=5, text="task2")]
    assert storage.next_id(todos) == 6


def test_todo_from_dict_accepts_positive_ids() -> None:
    """Todo.from_dict should accept valid positive IDs."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1

    todo = Todo.from_dict({"id": 999, "text": "task2"})
    assert todo.id == 999
