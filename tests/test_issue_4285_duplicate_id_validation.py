"""Tests for issue #4285: Duplicate todo ID validation in storage.load()."""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_duplicate_ids(tmp_path) -> None:
    """Bug #4285: storage.load() should reject JSON with duplicate IDs."""
    db = tmp_path / "duplicate_ids.json"
    storage = TodoStorage(str(db))

    # Create JSON with duplicate IDs
    duplicate_payload = [
        {"id": 1, "text": "first todo"},
        {"id": 2, "text": "second todo"},
        {"id": 1, "text": "duplicate of first"},
    ]
    db.write_text(json.dumps(duplicate_payload), encoding="utf-8")

    # Should raise ValueError for duplicate IDs
    with pytest.raises(ValueError, match=r"(?i)duplicate.*id") as exc_info:
        storage.load()

    # Error message should mention the duplicate ID
    assert "1" in str(exc_info.value)


def test_storage_load_rejects_multiple_duplicate_ids(tmp_path) -> None:
    """Bug #4285: storage.load() should report when multiple IDs are duplicated."""
    db = tmp_path / "multiple_duplicates.json"
    storage = TodoStorage(str(db))

    # Create JSON with multiple duplicate IDs
    duplicate_payload = [
        {"id": 1, "text": "first todo"},
        {"id": 1, "text": "duplicate of first"},
        {"id": 2, "text": "second todo"},
        {"id": 2, "text": "duplicate of second"},
    ]
    db.write_text(json.dumps(duplicate_payload), encoding="utf-8")

    # Should raise ValueError for duplicate IDs
    with pytest.raises(ValueError, match=r"(?i)duplicate.*id"):
        storage.load()


def test_storage_load_accepts_unique_ids(tmp_path) -> None:
    """Bug #4285: storage.load() should still work with unique IDs."""
    db = tmp_path / "unique_ids.json"
    storage = TodoStorage(str(db))

    # Create JSON with unique IDs
    unique_payload = [
        {"id": 1, "text": "first todo"},
        {"id": 2, "text": "second todo"},
        {"id": 3, "text": "third todo"},
    ]
    db.write_text(json.dumps(unique_payload), encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 3
    assert [t.id for t in loaded] == [1, 2, 3]


def test_storage_load_accepts_empty_list(tmp_path) -> None:
    """Bug #4285: storage.load() should still work with empty list."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    # Create empty JSON list
    db.write_text("[]", encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert loaded == []


def test_storage_load_accepts_single_item(tmp_path) -> None:
    """Bug #4285: storage.load() should work with single item (no duplicates possible)."""
    db = tmp_path / "single.json"
    storage = TodoStorage(str(db))

    # Create JSON with single item
    single_payload = [{"id": 1, "text": "only todo"}]
    db.write_text(json.dumps(single_payload), encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].id == 1
