"""Tests for duplicate ID validation when loading from JSON (Issue #3791).

These tests verify that:
1. Loading JSON with duplicate IDs raises ValueError
2. Error message clearly indicates which ID is duplicated
3. Loading JSON with unique IDs succeeds
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_duplicate_ids(tmp_path) -> None:
    """Loading JSON with duplicate IDs should raise ValueError."""
    db = tmp_path / "duplicate_ids.json"
    storage = TodoStorage(str(db))

    # Create JSON with duplicate IDs
    db.write_text('[{"id": 1, "text": "task a"}, {"id": 1, "text": "task b"}]', encoding="utf-8")

    # Should raise ValueError with clear message about duplicate ID
    with pytest.raises(ValueError, match=r"(?i)duplicate.*id"):
        storage.load()


def test_storage_load_rejects_duplicate_ids_multiple_occurrences(tmp_path) -> None:
    """Loading JSON with multiple occurrences of the same ID should raise ValueError."""
    db = tmp_path / "multiple_duplicates.json"
    storage = TodoStorage(str(db))

    # Create JSON with the same ID appearing 3 times
    db.write_text(
        '[{"id": 5, "text": "task a"}, {"id": 5, "text": "task b"}, {"id": 5, "text": "task c"}]',
        encoding="utf-8",
    )

    # Should raise ValueError
    with pytest.raises(ValueError, match=r"(?i)duplicate.*id"):
        storage.load()


def test_storage_load_accepts_unique_ids(tmp_path) -> None:
    """Loading JSON with unique IDs should succeed."""
    db = tmp_path / "unique_ids.json"
    storage = TodoStorage(str(db))

    # Create JSON with unique IDs
    db.write_text(
        '[{"id": 1, "text": "task a"}, {"id": 2, "text": "task b"}, {"id": 3, "text": "task c"}]',
        encoding="utf-8",
    )

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 3
    assert [t.id for t in todos] == [1, 2, 3]


def test_storage_load_error_message_includes_duplicate_id(tmp_path) -> None:
    """Error message should indicate which ID is duplicated."""
    db = tmp_path / "specific_duplicate.json"
    storage = TodoStorage(str(db))

    # Create JSON with a specific duplicate ID (42)
    db.write_text(
        '[{"id": 1, "text": "task a"}, {"id": 42, "text": "task b"}, {"id": 42, "text": "task c"}]',
        encoding="utf-8",
    )

    # Should raise ValueError that includes the duplicate ID value (42)
    with pytest.raises(ValueError, match=r"42"):
        storage.load()


def test_storage_load_empty_list_succeeds(tmp_path) -> None:
    """Loading empty JSON array should succeed (no duplicates possible)."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    db.write_text("[]", encoding="utf-8")

    todos = storage.load()
    assert todos == []
