"""Regression test for issue #2250: No validation for duplicate todo IDs.

This test verifies that loading a JSON file with duplicate todo IDs is properly rejected.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_duplicate_ids(tmp_path) -> None:
    """Bug #2250: Loading JSON with duplicate todo IDs should raise clear error."""
    db = tmp_path / "duplicates.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with duplicate IDs
    data = [
        {"id": 1, "text": "first todo", "done": False},
        {"id": 2, "text": "second todo", "done": True},
        {"id": 1, "text": "duplicate id", "done": False},  # Duplicate ID
    ]
    db.write_text(json.dumps(data), encoding="utf-8")

    # Should raise ValueError for duplicate IDs
    with pytest.raises(ValueError, match=r"Duplicate.*ID"):
        storage.load()


def test_storage_load_accepts_unique_ids(tmp_path) -> None:
    """Bug #2250: Verify JSON with unique IDs is still accepted."""
    db = tmp_path / "unique.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with unique IDs
    data = [
        {"id": 1, "text": "first todo", "done": False},
        {"id": 2, "text": "second todo", "done": True},
        {"id": 3, "text": "third todo", "done": False},
    ]
    db.write_text(json.dumps(data), encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 3
    assert loaded[0].id == 1
    assert loaded[1].id == 2
    assert loaded[2].id == 3


def test_storage_load_error_message_includes_duplicate_id_value(tmp_path) -> None:
    """Bug #2250: Error message should include which ID is duplicated."""
    db = tmp_path / "dup_with_message.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with duplicate IDs
    data = [
        {"id": 5, "text": "first", "done": False},
        {"id": 5, "text": "duplicate", "done": False},
    ]
    db.write_text(json.dumps(data), encoding="utf-8")

    # Error message should include the duplicate ID value
    with pytest.raises(ValueError, match="5"):
        storage.load()
