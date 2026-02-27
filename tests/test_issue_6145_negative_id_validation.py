"""Tests for issue #6145: Negative ID validation.

Bug: next_id returns incorrect ID when todos contain negative IDs.
When todos have negative IDs (e.g., -5), max() returns negative,
so next_id returns -4 instead of 1.

Fix: Validate that Todo IDs are positive in Todo.from_dict.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Bug #6145: Todo.from_dict should reject negative IDs."""
    with pytest.raises(ValueError, match="must be a positive integer"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Bug #6145: Todo.from_dict should reject zero as ID."""
    with pytest.raises(ValueError, match="must be a positive integer"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Verify positive IDs are still accepted."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1

    todo = Todo.from_dict({"id": 100, "text": "another test"})
    assert todo.id == 100


def test_next_id_returns_positive_when_todos_contain_negative_ids(tmp_path) -> None:
    """Bug #6145: next_id should always return positive integer >= 1.

    This test verifies the defensive programming in next_id.
    Even if negative IDs somehow exist in storage, next_id should
    never return a negative or zero value.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos with negative IDs directly (bypassing from_dict validation)
    # This simulates corrupted or maliciously crafted data
    todos = [Todo(id=-5, text="negative"), Todo(id=-1, text="another negative")]
    storage.save(todos)

    # next_id should return at least 1, not -4
    result = storage.next_id(todos)
    assert result >= 1, f"next_id returned {result}, expected >= 1"


def test_next_id_with_empty_list_returns_one(tmp_path) -> None:
    """Verify next_id returns 1 for empty list."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    result = storage.next_id([])
    assert result == 1


def test_next_id_with_positive_ids_returns_max_plus_one(tmp_path) -> None:
    """Verify next_id works correctly with positive IDs."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="first"), Todo(id=5, text="second")]
    result = storage.next_id(todos)
    assert result == 6
