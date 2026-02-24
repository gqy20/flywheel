"""Tests for negative ID validation (Issue #5624).

These tests verify that:
1. Todo.from_dict raises ValueError when 'id' field is negative
2. TodoStorage.load() rejects JSON with negative IDs
3. TodoStorage.next_id always returns positive integer (>=1)
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative integers for 'id' field."""
    with pytest.raises(ValueError, match=r"negative|'id'.*positive|'id'.*>=\s*0"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_large_negative_id() -> None:
    """Todo.from_dict should reject large negative integers for 'id' field."""
    with pytest.raises(ValueError, match=r"negative|'id'.*positive|'id'.*>=\s*0"):
        Todo.from_dict({"id": -999999, "text": "task"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept zero as a valid (non-negative) ID."""
    todo = Todo.from_dict({"id": 0, "text": "task"})
    assert todo.id == 0


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive integers for 'id' field."""
    todo = Todo.from_dict({"id": 42, "text": "task"})
    assert todo.id == 42


def test_storage_load_rejects_negative_id(tmp_path) -> None:
    """TodoStorage.load should reject JSON with negative ID."""
    db = tmp_path / "negative_id.json"
    storage = TodoStorage(str(db))

    # Valid JSON but with negative 'id'
    db.write_text('[{"id": -1, "text": "task"}]', encoding="utf-8")

    # Should raise clear error about negative 'id'
    with pytest.raises(ValueError, match=r"negative|'id'.*positive|'id'.*>=\s*0"):
        storage.load()


def test_next_id_returns_positive_for_empty_list() -> None:
    """next_id should return 1 for an empty todo list."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1


def test_next_id_returns_positive_with_positive_ids() -> None:
    """next_id should return max_id + 1 when existing IDs are positive."""
    storage = TodoStorage()
    todos = [Todo(id=5, text="task1"), Todo(id=10, text="task2")]
    result = storage.next_id(todos)
    assert result == 11


def test_next_id_returns_positive_regardless_of_existing_ids() -> None:
    """next_id should always return a positive integer even if existing IDs are unusual.

    This test ensures that even if somehow negative IDs got into the system,
    next_id would still return a valid positive ID.
    """
    storage = TodoStorage()
    # Create todos directly (bypassing from_dict validation for this test)
    # This simulates the scenario where bad data might already exist
    todo1 = Todo.__new__(Todo)
    todo1.id = -5
    todo1.text = "bad task"
    todo1.done = False
    todo1.created_at = ""
    todo1.updated_at = ""

    todo2 = Todo.__new__(Todo)
    todo2.id = -10
    todo2.text = "another bad task"
    todo2.done = False
    todo2.created_at = ""
    todo2.updated_at = ""

    todos = [todo1, todo2]

    # next_id should still return a positive integer
    result = storage.next_id(todos)
    assert result >= 1, f"next_id returned {result}, expected positive integer"
