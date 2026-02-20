"""Tests for issue #4736: ID collision when todos have duplicate IDs.

This test suite verifies that TodoStorage.load() properly validates
that JSON files do not contain duplicate IDs, preventing data corruption
and ID collision issues.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage


def test_load_rejects_duplicate_ids(tmp_path) -> None:
    """Test that load() raises ValueError when JSON contains duplicate IDs."""
    db = tmp_path / "duplicate.json"
    storage = TodoStorage(str(db))

    # Create JSON with duplicate IDs (corrupted data)
    corrupted_data = [
        {"id": 5, "text": "first todo with id 5"},
        {"id": 5, "text": "second todo with same id 5"},
    ]
    db.write_text(json.dumps(corrupted_data), encoding="utf-8")

    # Should raise ValueError for duplicate IDs
    with pytest.raises(ValueError, match=r"duplicate.*id|Duplicate ID"):
        storage.load()


def test_load_accepts_unique_ids(tmp_path) -> None:
    """Verify load() accepts valid JSON with unique IDs."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Create valid JSON with unique IDs
    valid_data = [
        {"id": 1, "text": "first todo"},
        {"id": 2, "text": "second todo"},
        {"id": 10, "text": "third todo with gap"},
    ]
    db.write_text(json.dumps(valid_data), encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 3
    assert [t.id for t in loaded] == [1, 2, 10]


def test_next_id_with_non_contiguous_ids(tmp_path) -> None:
    """Test that next_id() returns max+1 for non-contiguous IDs.

    This is a secondary test from the acceptance criteria:
    next_id() with non-contiguous IDs [1, 5, 10] returns 11 (max+1)
    """
    db = tmp_path / "noncontiguous.json"
    storage = TodoStorage(str(db))

    # Create JSON with non-contiguous IDs
    data = [
        {"id": 1, "text": "todo 1"},
        {"id": 5, "text": "todo 5"},
        {"id": 10, "text": "todo 10"},
    ]
    db.write_text(json.dumps(data), encoding="utf-8")

    loaded = storage.load()
    # next_id should return max(id) + 1 = 11
    assert storage.next_id(loaded) == 11


def test_load_empty_list_has_no_duplicates(tmp_path) -> None:
    """Verify empty JSON list is valid (no duplicates possible)."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    db.write_text("[]", encoding="utf-8")

    loaded = storage.load()
    assert loaded == []


def test_load_single_item_has_no_duplicates(tmp_path) -> None:
    """Verify single-item JSON is valid (can't have duplicates with one item)."""
    db = tmp_path / "single.json"
    storage = TodoStorage(str(db))

    data = [{"id": 1, "text": "only todo"}]
    db.write_text(json.dumps(data), encoding="utf-8")

    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].id == 1
