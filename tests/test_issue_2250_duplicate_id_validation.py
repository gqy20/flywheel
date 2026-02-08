"""Regression test for issue #2250: No validation for duplicate todo IDs.

This test verifies that the storage layer properly validates and rejects
JSON data containing duplicate todo IDs, which could otherwise lead to
data corruption and incorrect behavior.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_load_rejects_duplicate_ids(tmp_path) -> None:
    """Bug #2250: Loading JSON with duplicate IDs should raise ValueError."""
    db = tmp_path / "duplicate_ids.json"
    storage = TodoStorage(str(db))

    # Create JSON with duplicate IDs (two todos with id=1)
    duplicate_data = [
        {"id": 1, "text": "first todo", "done": False},
        {"id": 1, "text": "duplicate id", "done": False},
        {"id": 2, "text": "third todo", "done": True},
    ]
    db.write_text(json.dumps(duplicate_data), encoding="utf-8")

    # Should raise ValueError for duplicate IDs
    with pytest.raises(ValueError, match=r"(?i)duplicate.*id"):
        storage.load()


def test_storage_load_accepts_unique_ids(tmp_path) -> None:
    """Bug #2250: Loading JSON with unique IDs should work normally."""
    db = tmp_path / "unique_ids.json"
    storage = TodoStorage(str(db))

    # Create JSON with unique IDs
    unique_data = [
        {"id": 1, "text": "first todo", "done": False},
        {"id": 2, "text": "second todo", "done": True},
        {"id": 3, "text": "third todo", "done": False},
    ]
    db.write_text(json.dumps(unique_data), encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 3
    assert loaded[0].id == 1
    assert loaded[1].id == 2
    assert loaded[2].id == 3


def test_next_id_handles_duplicate_ids_gracefully(tmp_path) -> None:
    """Bug #2250: next_id() should still work correctly even if duplicates exist.

    This is a defensive test - if duplicates somehow get into the system,
    next_id() should still return a value that won't cause more conflicts.
    """
    storage = TodoStorage(str(tmp_path / "test.json"))

    # Create a list with duplicate IDs (simulating corrupted data)
    todos_with_duplicates = [
        Todo(id=1, text="first"),
        Todo(id=1, text="duplicate"),
        Todo(id=3, text="third"),
    ]

    # next_id should return 4 (max of 1, 1, 3 + 1), not 2
    next_id = storage.next_id(todos_with_duplicates)
    assert next_id == 4
