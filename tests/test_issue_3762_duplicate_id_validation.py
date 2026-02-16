"""Tests for duplicate id validation (Issue #3762).

These tests verify that:
1. storage.load() rejects JSON files with duplicate ids
2. This prevents data integrity issues where next_id() assumes unique ids
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_duplicate_ids(tmp_path) -> None:
    """storage.load() should reject JSON with duplicate ids to protect data integrity.

    Regression test for issue #3762:
    - Todo.from_dict allows creating duplicate id Todos
    - storage.next_id assumes all ids are unique (max+1)
    - Duplicate ids break mark_done/remove which match on first occurrence
    """
    db = tmp_path / "duplicate_ids.json"
    storage = TodoStorage(str(db))

    # Create JSON with duplicate id=1 appearing twice
    db.write_text(
        '[{"id": 1, "text": "first task"}, {"id": 1, "text": "duplicate task"}]',
        encoding="utf-8",
    )

    # Should raise clear error about duplicate ids
    with pytest.raises(ValueError, match=r"duplicate.*id|id.*unique|id.*conflict"):
        storage.load()


def test_storage_load_accepts_unique_ids(tmp_path) -> None:
    """storage.load() should accept JSON with unique ids."""
    db = tmp_path / "unique_ids.json"
    storage = TodoStorage(str(db))

    # Create JSON with unique ids
    db.write_text(
        '[{"id": 1, "text": "first task"}, {"id": 2, "text": "second task"}]',
        encoding="utf-8",
    )

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[1].id == 2


def test_storage_load_rejects_multiple_duplicate_ids(tmp_path) -> None:
    """storage.load() should report which ids are duplicated."""
    db = tmp_path / "multiple_duplicates.json"
    storage = TodoStorage(str(db))

    # Create JSON with multiple duplicate ids
    db.write_text(
        '[{"id": 1, "text": "a"}, {"id": 1, "text": "b"}, {"id": 2, "text": "c"}, {"id": 2, "text": "d"}]',
        encoding="utf-8",
    )

    # Should raise error mentioning at least one of the duplicate ids
    with pytest.raises(ValueError, match=r"duplicate.*id|id.*unique"):
        storage.load()


def test_next_id_remains_consistent_after_valid_load(tmp_path) -> None:
    """After loading valid data, next_id should return correct value."""
    db = tmp_path / "valid_data.json"
    storage = TodoStorage(str(db))

    # Create JSON with max id=5
    db.write_text(
        '[{"id": 1, "text": "a"}, {"id": 3, "text": "b"}, {"id": 5, "text": "c"}]',
        encoding="utf-8",
    )

    todos = storage.load()
    next_id = storage.next_id(todos)

    # next_id should be max(existing_ids) + 1 = 6
    assert next_id == 6
