"""Tests for TodoStorage.count() method - Issue #4822.

Feature: Add count() method to return todo count without full load.

Acceptance criteria:
- count() returns 0 when storage file does not exist
- count() returns correct integer count of stored todos
- count() raises ValueError for corrupted JSON (consistent with load())
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_count_returns_zero_when_storage_file_does_not_exist(tmp_path) -> None:
    """Test that count() returns 0 when the storage file does not exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File does not exist yet
    assert not db.exists()

    # count() should return 0 without creating the file
    assert storage.count() == 0


def test_count_returns_correct_count_of_stored_todos(tmp_path) -> None:
    """Test that count() returns the correct integer count of stored todos."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Add 3 todos
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]
    storage.save(todos)

    # count() should return 3
    assert storage.count() == 3


def test_count_returns_zero_for_empty_storage(tmp_path) -> None:
    """Test that count() returns 0 for storage with no todos."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    # Save empty list
    storage.save([])

    # count() should return 0
    assert storage.count() == 0


def test_count_raises_valueerror_for_corrupted_json(tmp_path) -> None:
    """Test that count() raises ValueError for corrupted JSON, consistent with load()."""
    db = tmp_path / "corrupted.json"
    storage = TodoStorage(str(db))

    # Write invalid JSON
    db.write_text("not valid json {", encoding="utf-8")

    # count() should raise ValueError (consistent with load())
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.count()


def test_count_raises_valueerror_for_non_list_json(tmp_path) -> None:
    """Test that count() raises ValueError if JSON is not a list."""
    db = tmp_path / "not_list.json"
    storage = TodoStorage(str(db))

    # Write valid JSON but not a list
    db.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

    # count() should raise ValueError (consistent with load())
    with pytest.raises(ValueError, match="must be a JSON list"):
        storage.count()
