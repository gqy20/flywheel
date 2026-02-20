"""Tests for duplicate ID validation in TodoStorage.

This test suite verifies that TodoStorage.load() raises ValueError when
the JSON file contains duplicate todo IDs, preventing ID collision issues.

Issue: #4736 - ID collision when todos have duplicate IDs
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_raises_value_error_on_duplicate_ids(tmp_path: Path) -> None:
    """Test that load() raises ValueError when JSON contains duplicate IDs.

    This prevents ID collision issues where next_id() would return an ID
    that already exists in the corrupted data.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with duplicate IDs (corrupted data)
    corrupted_data = [
        {"id": 1, "text": "first task", "done": False},
        {"id": 1, "text": "duplicate id task", "done": True},  # Duplicate ID!
        {"id": 2, "text": "third task", "done": False},
    ]
    db.write_text(json.dumps(corrupted_data), encoding="utf-8")

    # load() should raise ValueError with a clear message about duplicate IDs
    with pytest.raises(ValueError, match=r"Duplicate todo ID.*found in"):
        storage.load()


def test_load_accepts_unique_ids(tmp_path: Path) -> None:
    """Test that load() accepts JSON with all unique IDs."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file with unique IDs
    valid_data = [
        {"id": 1, "text": "first task", "done": False},
        {"id": 2, "text": "second task", "done": True},
        {"id": 5, "text": "third task", "done": False},  # Non-contiguous is OK
    ]
    db.write_text(json.dumps(valid_data), encoding="utf-8")

    # load() should succeed and return all todos
    todos = storage.load()
    assert len(todos) == 3
    assert [t.id for t in todos] == [1, 2, 5]


def test_load_with_single_todo_succeeds(tmp_path: Path) -> None:
    """Test that load() works with a single todo (no duplicate check needed)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    single_data = [{"id": 1, "text": "only task", "done": False}]
    db.write_text(json.dumps(single_data), encoding="utf-8")

    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].id == 1


def test_next_id_with_non_contiguous_ids(tmp_path: Path) -> None:
    """Test that next_id() returns max+1 even with non-contiguous IDs.

    This is a related acceptance criteria from the issue.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos with non-contiguous IDs
    todos = [
        Todo(id=1, text="first"),
        Todo(id=5, text="second"),
        Todo(id=10, text="third"),
    ]
    storage.save(todos)

    # Load and verify
    loaded = storage.load()
    assert len(loaded) == 3

    # next_id should return max+1 = 11
    next_id = storage.next_id(loaded)
    assert next_id == 11
