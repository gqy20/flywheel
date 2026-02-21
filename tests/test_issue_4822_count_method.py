"""Tests for issue #4822: Add count() method to return todo count without full load."""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_count_returns_0_when_storage_file_does_not_exist(tmp_path) -> None:
    """count() returns 0 when storage file does not exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    assert storage.count() == 0


def test_count_returns_correct_count_of_stored_todos(tmp_path) -> None:
    """count() returns correct integer count of stored todos."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save 3 todos
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]
    storage.save(todos)

    # count() should return 3
    assert storage.count() == 3


def test_count_returns_0_for_empty_storage(tmp_path) -> None:
    """count() returns 0 for empty storage (file exists but empty list)."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    # Save empty list
    storage.save([])

    assert storage.count() == 0


def test_count_raises_valueerror_for_corrupted_json(tmp_path) -> None:
    """count() raises ValueError for corrupted JSON (consistent with load())."""
    db = tmp_path / "corrupted.json"
    storage = TodoStorage(str(db))

    # Write invalid JSON
    db.write_text("{ invalid json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.count()


def test_count_raises_valueerror_for_non_list_json(tmp_path) -> None:
    """count() raises ValueError when JSON is not a list (consistent with load())."""
    db = tmp_path / "notalist.json"
    storage = TodoStorage(str(db))

    # Write valid JSON that is not a list
    db.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

    with pytest.raises(ValueError, match="must be a JSON list"):
        storage.count()
