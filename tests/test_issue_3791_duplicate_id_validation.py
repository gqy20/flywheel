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

    # Create a file with duplicate IDs
    db.write_text(
        '[{"id": 1, "text": "task a"}, {"id": 1, "text": "task b"}]',
        encoding="utf-8",
    )

    # Should raise ValueError indicating duplicate ID
    with pytest.raises(ValueError, match=r"duplicate.*id|id.*duplicate|unique"):
        storage.load()


def test_storage_load_duplicate_id_error_message_contains_id(tmp_path) -> None:
    """Error message for duplicate IDs should indicate which ID is duplicated."""
    db = tmp_path / "duplicate_ids_msg.json"
    storage = TodoStorage(str(db))

    db.write_text(
        '[{"id": 42, "text": "first"}, {"id": 42, "text": "second"}]',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"42"):
        storage.load()


def test_storage_load_accepts_unique_ids(tmp_path) -> None:
    """Loading JSON with unique IDs should succeed."""
    db = tmp_path / "unique_ids.json"
    storage = TodoStorage(str(db))

    db.write_text(
        '[{"id": 1, "text": "task a"}, {"id": 2, "text": "task b"}]',
        encoding="utf-8",
    )

    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[1].id == 2


def test_storage_load_empty_list_succeeds(tmp_path) -> None:
    """Loading empty JSON list should succeed (no duplicates to check)."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    db.write_text("[]", encoding="utf-8")

    todos = storage.load()
    assert todos == []


def test_storage_load_single_item_succeeds(tmp_path) -> None:
    """Loading JSON with a single item should succeed (no duplicates possible)."""
    db = tmp_path / "single.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "only task"}]', encoding="utf-8")

    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].id == 1
