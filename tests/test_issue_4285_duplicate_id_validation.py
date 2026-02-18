"""Tests for duplicate todo ID validation (Issue #4285).

These tests verify that:
1. storage.load() raises ValueError when JSON contains duplicate IDs
2. Error message includes the duplicate ID value
3. Normal files without duplicates load successfully
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_duplicate_ids(tmp_path) -> None:
    """storage.load() should raise ValueError when JSON contains duplicate IDs."""
    db = tmp_path / "duplicate_ids.json"
    storage = TodoStorage(str(db))

    # Create a file with duplicate IDs (id=1 appears twice)
    db.write_text(
        '[{"id": 1, "text": "task one"}, {"id": 2, "text": "task two"}, {"id": 1, "text": "duplicate task"}]',
        encoding="utf-8",
    )

    # Should raise ValueError with clear message about duplicate ID
    with pytest.raises(ValueError, match=r"(?i)duplicate.*id.*1|duplicate.*1"):
        storage.load()


def test_storage_load_rejects_duplicate_ids_error_message(tmp_path) -> None:
    """storage.load() error message should include the duplicate ID value."""
    db = tmp_path / "duplicate_id_message.json"
    storage = TodoStorage(str(db))

    # Create a file with duplicate IDs
    db.write_text(
        '[{"id": 42, "text": "first"}, {"id": 42, "text": "second"}]',
        encoding="utf-8",
    )

    # Error message should include "42" as the duplicate ID
    with pytest.raises(ValueError, match="42"):
        storage.load()


def test_storage_load_accepts_unique_ids(tmp_path) -> None:
    """storage.load() should successfully load files with unique IDs."""
    db = tmp_path / "unique_ids.json"
    storage = TodoStorage(str(db))

    # Create a file with unique IDs
    db.write_text(
        '[{"id": 1, "text": "task one"}, {"id": 2, "text": "task two"}, {"id": 3, "text": "task three"}]',
        encoding="utf-8",
    )

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 3
    assert todos[0].id == 1
    assert todos[1].id == 2
    assert todos[2].id == 3


def test_storage_load_empty_list(tmp_path) -> None:
    """storage.load() should handle empty lists without duplicates."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    db.write_text("[]", encoding="utf-8")

    todos = storage.load()
    assert len(todos) == 0


def test_storage_load_single_item(tmp_path) -> None:
    """storage.load() should handle single item lists without duplicates."""
    db = tmp_path / "single.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "only task"}]', encoding="utf-8")

    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].id == 1
