"""Tests for duplicate ID validation in storage.load() (Issue #3762).

These tests verify that:
1. storage.load() rejects JSON files containing duplicate todo IDs
2. A clear error message is provided when duplicate IDs are detected
3. This maintains data integrity assumptions used by next_id()
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_duplicate_ids(tmp_path) -> None:
    """storage.load() should reject JSON with duplicate IDs to maintain data integrity."""
    db = tmp_path / "duplicate_ids.json"
    storage = TodoStorage(str(db))

    # Create a file with duplicate IDs
    db.write_text(
        '[{"id": 1, "text": "first task"}, {"id": 1, "text": "duplicate id"}]',
        encoding="utf-8",
    )

    # Should raise ValueError with clear message about duplicate IDs
    with pytest.raises(ValueError, match=r"(?i)duplicate.*id|id.*unique"):
        storage.load()


def test_storage_load_rejects_multiple_duplicate_ids(tmp_path) -> None:
    """storage.load() should reject JSON with multiple duplicate IDs."""
    db = tmp_path / "multiple_duplicates.json"
    storage = TodoStorage(str(db))

    # Create a file with multiple duplicate IDs
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}, {"id": 1, "text": "duplicate of 1"}, {"id": 2, "text": "duplicate of 2"}]',
        encoding="utf-8",
    )

    # Should raise ValueError
    with pytest.raises(ValueError, match=r"(?i)duplicate.*id|id.*unique"):
        storage.load()


def test_storage_load_accepts_unique_ids(tmp_path) -> None:
    """storage.load() should accept JSON with unique IDs (normal case)."""
    db = tmp_path / "unique_ids.json"
    storage = TodoStorage(str(db))

    # Create a file with unique IDs
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}, {"id": 3, "text": "task3"}]',
        encoding="utf-8",
    )

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 3
    assert [t.id for t in todos] == [1, 2, 3]


def test_error_message_includes_duplicate_id(tmp_path) -> None:
    """Error message should include the duplicate ID value for debugging."""
    db = tmp_path / "duplicate.json"
    storage = TodoStorage(str(db))

    db.write_text(
        '[{"id": 42, "text": "first"}, {"id": 42, "text": "duplicate"}]',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"42"):
        storage.load()
