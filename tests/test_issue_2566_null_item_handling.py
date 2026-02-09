"""Tests for null item handling in JSON array (Issue #2566).

These tests verify that:
1. Null items in JSON arrays are handled gracefully
2. Clear error messages are provided indicating the invalid item index
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_handles_null_items_in_json_array(tmp_path) -> None:
    """Null items in JSON array should produce clear error message with index."""
    db = tmp_path / "null_items.json"
    storage = TodoStorage(str(db))

    # Valid JSON with null items interspersed
    db.write_text('[{"id": 1, "text": "valid task"}, null, {"id": 2, "text": "also valid"}]', encoding="utf-8")

    # Should raise ValueError with clear message about null item
    with pytest.raises(ValueError, match=r"null|item.*1|index.*1"):
        storage.load()


def test_storage_load_handles_null_at_start_of_array(tmp_path) -> None:
    """Null as first item in JSON array should produce clear error message."""
    db = tmp_path / "null_first.json"
    storage = TodoStorage(str(db))

    # Valid JSON with null as first item
    db.write_text('[null, {"id": 1, "text": "task"}]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"null|item.*0|index.*0"):
        storage.load()


def test_storage_load_handles_all_null_items(tmp_path) -> None:
    """JSON array with only null items should produce clear error message."""
    db = tmp_path / "all_null.json"
    storage = TodoStorage(str(db))

    # Valid JSON with all null items
    db.write_text('[null, null, null]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"null"):
        storage.load()


def test_storage_load_handles_valid_items_only(tmp_path) -> None:
    """JSON array with valid items only should load successfully."""
    db = tmp_path / "valid_only.json"
    storage = TodoStorage(str(db))

    # Valid JSON with no null items
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "task1"
    assert loaded[1].text == "task2"
