"""Tests for issue #4736: Duplicate ID detection in TodoStorage.load().

Bug: ID collision when todos have duplicate IDs - next_id() does not check
for existing ID conflicts.

Fix: load() should raise ValueError when JSON contains duplicate IDs to
prevent data corruption from propagating through the application.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage


def test_load_raises_value_error_on_duplicate_ids(tmp_path) -> None:
    """load() should raise ValueError when JSON contains duplicate IDs.

    This prevents corrupted data with duplicate IDs from causing
    ID collisions when next_id() is called.
    """
    db = tmp_path / "duplicate_ids.json"
    storage = TodoStorage(str(db))

    # Create JSON with duplicate IDs (corrupted data)
    corrupted_data = [
        {"id": 5, "text": "first todo with id 5"},
        {"id": 5, "text": "second todo with id 5 - duplicate!"},
    ]
    db.write_text(json.dumps(corrupted_data), encoding="utf-8")

    # load() should raise ValueError with clear message about duplicates
    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value).lower()
    assert "duplicate" in error_msg
    assert "id" in error_msg


def test_load_accepts_valid_unique_ids(tmp_path) -> None:
    """load() should accept valid data with unique IDs.

    This is a regression test to ensure the fix doesn't break normal usage.
    """
    db = tmp_path / "valid_ids.json"
    storage = TodoStorage(str(db))

    valid_data = [
        {"id": 1, "text": "first"},
        {"id": 2, "text": "second"},
        {"id": 5, "text": "fifth (non-contiguous is OK)"},
    ]
    db.write_text(json.dumps(valid_data), encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 3
    assert [t.id for t in loaded] == [1, 2, 5]


def test_load_accepts_empty_list(tmp_path) -> None:
    """load() should accept empty list as valid (no duplicates possible)."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    db.write_text("[]", encoding="utf-8")

    # Should load successfully as empty list
    loaded = storage.load()
    assert loaded == []


def test_load_accepts_single_item(tmp_path) -> None:
    """load() should accept single item as valid (no duplicates possible)."""
    db = tmp_path / "single.json"
    storage = TodoStorage(str(db))

    db.write_text(json.dumps([{"id": 1, "text": "only one"}]), encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].id == 1


def test_next_id_with_non_contiguous_ids(tmp_path) -> None:
    """next_id() should return max_id + 1 for non-contiguous IDs.

    This verifies that the original behavior of next_id() is preserved.
    """
    db = tmp_path / "non_contiguous.json"
    storage = TodoStorage(str(db))

    valid_data = [
        {"id": 1, "text": "first"},
        {"id": 5, "text": "fifth"},
        {"id": 10, "text": "tenth"},
    ]
    db.write_text(json.dumps(valid_data), encoding="utf-8")

    loaded = storage.load()
    # next_id should return 11 (max + 1)
    assert storage.next_id(loaded) == 11


def test_error_message_includes_duplicate_id_value(tmp_path) -> None:
    """The error message should include the duplicate ID value for debugging."""
    db = tmp_path / "duplicate_ids_message.json"
    storage = TodoStorage(str(db))

    corrupted_data = [
        {"id": 42, "text": "first"},
        {"id": 42, "text": "duplicate of 42"},
    ]
    db.write_text(json.dumps(corrupted_data), encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    # Error message should mention the duplicate ID value
    assert "42" in str(exc_info.value)


def test_multiple_duplicate_ids_detected(tmp_path) -> None:
    """load() should detect duplicates even if there are multiple different duplicates."""
    db = tmp_path / "multiple_duplicates.json"
    storage = TodoStorage(str(db))

    corrupted_data = [
        {"id": 1, "text": "first 1"},
        {"id": 1, "text": "second 1 - duplicate!"},
        {"id": 2, "text": "first 2"},
        {"id": 2, "text": "second 2 - also duplicate!"},
    ]
    db.write_text(json.dumps(corrupted_data), encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value).lower()
    assert "duplicate" in error_msg
